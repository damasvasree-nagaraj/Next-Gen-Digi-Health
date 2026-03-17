from flask import Flask, request, jsonify, render_template, redirect, session, url_for, flash
from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from urllib.parse import quote_plus
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from flask import send_file
from io import BytesIO
from reportlab.pdfgen import canvas
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
import random
import certifi
import requests
import os
from dotenv import load_dotenv

load_dotenv()

from functools import wraps

def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_role") != "doctor":
            return redirect("/select-role")
        return f(*args, **kwargs)
    return decorated_function

# ================= APP SETUP =================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")
bcrypt = Bcrypt(app)

# ================= DATABASE =================
MONGO_USERNAME= os.getenv("MONGO_USERNAME")
MONGO_PASSWORD=quote_plus(os.getenv("MONGO_PASSWORD"))

MONGO_URI = (
    f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}"
    "@cluster0.grbxsig.mongodb.net/next_gen_digi_health"
    "?retryWrites=true&w=majority"
)

client = MongoClient(MONGO_URI, tls=True, tlsCAFile=certifi.where())
db = client["next_gen_digi_health"]

users = db["users"]
orders = db["orders"]
prescriptions = db["prescriptions"]
medical_records = db["medical_records"]
appointments = db["appointments"]
insurance_claims = db["insurance_claims"]

# =========================================================
# HOME
# =========================================================
@app.route("/")
def home():
    return redirect("/select-role")


@app.route("/select-role")
def select_role():
    return render_template("select_role.html")


# =========================================================
# LOGIN PAGES
# =========================================================
@app.route("/register-page")
def register_page():
    return render_template("register.html")

@app.route("/register", methods=["POST"])
def register():

    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "patient")

    # Check if user already exists
    if users.find_one({"email": email}):
        return jsonify({"error": "User already exists"})

    # Hash password
    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    # Save user
    users.insert_one({
        "name": name,
        "email": email,
        "password": hashed_password,
        "role": role,
        "created_at": datetime.now()
    })

    # ✅ SEND EMAIL HERE
    send_confirmation_email(
        email,
        name,
        "Digi Health Team",
        "Welcome",
        "Now"
    )

    return jsonify({"message": "Registration successful"})

@app.route("/login/patient")
def patient_login_page():
    return render_template("index.html")


@app.route("/login/doctor")
def doctor_login_page():
    return render_template("doctor_login.html")


# =========================================================
# LOGIN (JSON BASED)
# =========================================================
@app.route("/login", methods=["POST"])
def login():

    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = users.find_one({"email": email})

    if not user:
        return jsonify({"error": "User not found"})

    if not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"error": "Wrong password"})

    session.clear()

    session["user_id"] = str(user["_id"])
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]
    session["user_role"] = user["role"]

    if user["role"] == "patient":
        return jsonify({"redirect": "/welcome"})

    if user["role"] == "doctor":
        return jsonify({"redirect": "/doctor"})

    if user["role"] == "hospital_admin":
        session["hospital_admin"] = str(user["_id"])
        return jsonify({"redirect": "/hospital/dashboard"})

    return jsonify({"error": "Invalid role"})


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/select-role")


# =========================================================
# PATIENT MODULE (UNCHANGED WORKING)
# =========================================================
@app.route("/welcome")
def welcome():
    if session.get("user_role") != "patient":
        return redirect("/select-role")
    return render_template("welcome.html")


@app.route("/profile")
def profile():
    if session.get("user_role") != "patient":
        return redirect("/select-role")

    user = users.find_one({"_id": ObjectId(session["user_id"])})
    return render_template("profile.html", user=user)


@app.route("/pharmacy")
def pharmacy():
    if session.get("user_role") != "patient":
        return redirect("/select-role")
    return render_template("pharmacy.html")


@app.route("/cart")
def cart():
    if session.get("user_role") != "patient":
        return redirect("/select-role")
    return render_template("cart.html")


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if session.get("user_role") != "patient":
        return redirect("/select-role")

    if request.method == "POST":
        data = request.get_json()
        orders.insert_one({
            "customer": session["user_email"],
            "items": data.get("items", []),
            "total": data.get("total"),
            "created_at": datetime.now(timezone.utc)
        })
        return jsonify({"redirect": "/order_success"})

    return render_template("checkout.html")


@app.route("/order_success")
def order_success():
    if session.get("user_role") != "patient":
        return redirect("/select-role")
    return render_template("order_success.html")


@app.route("/order_status")
def order_status():
    if session.get("user_role") != "patient":
        return redirect("/select-role")
    return render_template("order_status.html")


@app.route("/insurance")
def insurance():
    if session.get("user_role") != "patient":
        return redirect("/select-role")
    return render_template("insurance.html")


@app.route("/physio")
def physio():
    if session.get("user_role") != "patient":
        return redirect("/select-role")
    return render_template("physio.html")

@app.route("/my-prescriptions")
def my_prescriptions():
    if "user_id" not in session:
        return redirect("/login/patient")

    prescriptions = list(db.prescriptions.find({
        "patient_id": session["user_id"]
    }))

    return render_template(
        "patient_prescriptions.html",
        prescriptions=prescriptions
    )


@app.route("/upload-prescription", methods=["GET", "POST"])
def upload_prescription():

    if "user_id" not in session:
        return redirect("/login/patient")

    prescriptions = list(db.prescriptions.find({
        "patient_id": session["user_id"]
    }))

    return render_template(
        "upload_prescription.html",
        prescriptions=prescriptions
    )

@app.route("/download-prescription/<id>")
def download_prescription(id):

    prescription = db.prescriptions.find_one({
        "_id": ObjectId(id)
    })

    if not prescription:
        return "Prescription not found", 404

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, 800, "Digi Health - Prescription")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 760, f"Doctor: {prescription.get('doctor_name', '')}")
    pdf.drawString(100, 740, f"Patient: {prescription.get('patient_name', '')}")
    pdf.drawString(100, 720, f"Diagnosis: {prescription.get('diagnosis', '')}")
    pdf.drawString(100, 700, f"Medicines: {prescription.get('medicines', '')}")
    pdf.drawString(100, 680, f"Notes: {prescription.get('notes', '')}")

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="prescription.pdf",
        mimetype="application/pdf"
    )

def detect_fraud(claim):

    try:
        amount = int(claim.get("amount", 0))
    except:
        amount = 0

    # Rule 1: High amount
    if amount > 20000:
        return "High Risk"

    # Rule 2: Too many claims
    count = insurance_claims.count_documents({
        "patient_id": claim["patient_id"]
    })

    if count > 5:
        return "Frequent Claimer"

    return "Safe"

@app.route("/submit-claim", methods=["POST"])
def submit_claim():

    if session.get("user_role") != "patient":
        return redirect("/select-role")

    data = request.get_json()

    # ✅ SAFE amount conversion
    try:
        amount = int(data.get("amount", 0))
    except:
        amount = 0

    # Step 1: Create base claim
    claim_data = {
        "patient_id": session.get("user_id"),
        "patient_name": session.get("user_name"),
        "doctor_id": data.get("doctor_id"),
        "doctor_name": data.get("doctor_name"),
        "treatment": data.get("treatment"),
        "amount": amount,
        "status": "Pending",
        "created_at": datetime.now()
    }

    # Step 2: Fraud detection
    fraud_status = detect_fraud(claim_data)
    claim_data["fraud_flag"] = fraud_status

    # Step 3: Smart status decision
    if amount < 5000 and fraud_status == "Safe":
        claim_data["status"] = "Approved"
    elif fraud_status == "High Risk":
        claim_data["status"] = "Under Review"
    else:
        claim_data["status"] = "Pending"

    # Step 4: Save
    insurance_claims.insert_one(claim_data)

    return jsonify({"message": "Claim submitted successfully"})


# ================= AI IMPORTS =================
from ai_chatbot.ollama_client import call_ollama
from ai_chatbot.rag_engine import retrieve_context
from ai_chatbot.prompts import SYSTEM_PROMPT, build_user_prompt
from deep_translator import GoogleTranslator

def translate_to_english(text):
    try:
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        return translated
    except Exception as e:
        print("Translation to English failed:", e)
        return text


def translate_from_english(text, lang):
    try:
        lang = lang.split("-")[0]  # ta-IN -> ta
        translated = GoogleTranslator(source='en', target=lang).translate(text)
        return translated
    except Exception as e:
        print("Translation from English failed:", e)
        return text

# ================= CHATBOT (FINAL CLEAN VERSION) =================
@app.route("/chatbot")
def chatbot():
    if session.get("user_role") != "patient":
        return redirect("/select-role")
    return render_template("chatbot.html")

@app.route("/api/chat", methods=["POST"])
def chat_api():

    if session.get("user_role") != "patient":
        return jsonify({"reply": "Login required"}), 401

    data = request.get_json()

    user_message = data.get("message")
    user_lang = data.get("language", "en-US")

    if not user_message:
        return jsonify({"reply": "Please enter a message."})

    try:

        # Convert user language to English
        english_message = translate_to_english(user_message)

        context = retrieve_context(english_message)

        prompt = SYSTEM_PROMPT + build_user_prompt(context, english_message)

        ai_reply = call_ollama(prompt)

        # Translate AI reply back to user language
        final_reply = translate_from_english(ai_reply, user_lang)

        return jsonify({"reply": final_reply})

    except Exception as e:

        print("Chat Error:", e)

        return jsonify({"reply": "AI temporarily unavailable."})

@app.route('/video_call/<room>')
def video_call(room):
    return render_template("video_call.html", room=room)
# =========================================================
# DOCTOR MODULE (SAFE PLACEHOLDER)
# =========================================================
# =========================================================
# DOCTOR MODULE
# =========================================================

@app.route("/doctor")
@doctor_required
def doctor_dashboard():

    doctor_id = session.get("user_id")
    today = datetime.now().strftime("%Y-%m-%d")

    today_appointments = list(appointments.find({
    "doctor_id": doctor_id,
    "status": "Confirmed"
    }).sort("date", 1))

    available_slots = db.doctor_availability.count_documents({
        "doctor_id": doctor_id,
        "is_active": True
    })

    booked_slots = appointments.count_documents({
        "doctor_id": doctor_id,
        "status": "Confirmed"
    })

    utilization = round((booked_slots / available_slots) * 100, 2) if available_slots > 0 else 0

    total_today = len(today_appointments)
    completed = len([a for a in today_appointments if a.get("status") == "Completed"])
    cancelled = len([a for a in today_appointments if a.get("status") == "Cancelled"])

    return render_template(
        "doctor_dashboard.html",
        appointments=today_appointments,
        total_today=total_today,
        completed=completed,
        cancelled=cancelled,
        utilization=utilization
    )

@app.route("/doctor/video-appointments")
@doctor_required
def doctor_video_appointments():

    doctor_id = session.get("user_id")

    video_appointments = list(appointments.find({
        "doctor_id": doctor_id,
        "appointment_type": "video"
    }).sort("date", 1))

    return render_template(
        "doctor_video_appointments.html",
        appointments=video_appointments
    )


@app.route("/doctor/complete/<appointment_id>", methods=["POST"])
@doctor_required
def doctor_complete(appointment_id):

    appointments.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": {"status": "Completed"}}
    )

    return redirect("/doctor")

def generate_next_slot(doctor_id):
    """
    Simple automatic reschedule:
    Finds next available future slot for that doctor.
    """

    from datetime import datetime, timedelta

    today = datetime.now()

    # Try next 7 days
    for i in range(1, 8):
        next_date = (today + timedelta(days=i)).strftime("%Y-%m-%d")

        # Check doctor availability
        availability = db.doctor_availability.find_one({
            "doctor_id": doctor_id,
            "is_active": True
        })

        if not availability:
            continue

        start_time = availability.get("start_time")
        end_time = availability.get("end_time")

        if not start_time:
            continue

        # Simple logic: return first available time
        return next_date, start_time

    return None, None

@app.route('/doctor/appointments')
def doctor_appointments():

    doctor_id = session.get("user_id")

    doctor_appointments = db.appointments.find({
        "doctor_id": doctor_id
    })

    return render_template(
        "doctor_dashboard.html",
        appointments=doctor_appointments
    )


# ===============================
# DOCTOR CREATE PRESCRIPTION
# ===============================
@app.route("/doctor/prescriptions")
def doctor_prescriptions():

    if "user_role" not in session or session["user_role"] != "doctor":
        return redirect("/login/doctor")

    doctor_id = session.get("user_id")

    prescriptions = list(db.prescriptions.find({
        "doctor_id": doctor_id
    }))

    return render_template(
        "doctor_prescription.html",
        prescriptions=prescriptions
    )

@app.route("/doctor/prescribe", methods=["GET", "POST"])
def doctor_prescribe():

    if "user_role" not in session or session["user_role"] != "doctor":
        return redirect("/login/doctor")

    if request.method == "POST":
        patient_name = request.form["patient_name"]
        diagnosis = request.form["diagnosis"]
        medicines = request.form["medicines"]
        notes = request.form["notes"]

        # 🔍 Find patient
        patient = users.find_one({
            "name": patient_name,
            "role": "patient"
        })

        if not patient:
            return "Patient not found"

        db.prescriptions.insert_one({
            "doctor_id": session["user_id"],
            "doctor_name": session.get("user_name"),
            "patient_id": str(patient["_id"]),  # IMPORTANT
            "patient_name": patient_name,
            "diagnosis": diagnosis,
            "medicines": medicines,
            "notes": notes,
            "date": datetime.now().strftime("%Y-%m-%d")
        })

        return redirect("/doctor/prescriptions")

    return render_template("doctor_prescribe.html")


@app.route("/doctor/claims")
def doctor_claims():

    if "user_role" not in session or session["user_role"] != "doctor":
        return redirect("/login/doctor")

    doctor_id = session.get("user_id")

    claims = list(insurance_claims.find({ 
        "doctor_id": doctor_id
    }))

    return render_template(
        "doctor_claims.html",
        claims=claims
    )

@app.route("/doctor/approve-claim/<claim_id>", methods=["POST"])
def approve_claim(claim_id):

    if session.get("user_role") != "doctor":
        return redirect("/login/doctor")

    insurance_claims.update_one(
        {"_id": ObjectId(claim_id)},
        {"$set": {"status": "Approved"}}
    )

    return redirect("/doctor/claims")


@app.route("/doctor/reject-claim/<claim_id>", methods=["POST"])
def reject_claim(claim_id):

    if session.get("user_role") != "doctor":
        return redirect("/login/doctor")

    insurance_claims.update_one(
        {"_id": ObjectId(claim_id)},
        {"$set": {"status": "Rejected"}}
    )

    return redirect("/doctor/claims")

# =========================================================
# HOSPITAL MODULE (SAFE PLACEHOLDER)
# =========================================================
@app.route("/hospital/login", methods=["GET", "POST"])
def hospital_login():
    if request.method == "GET":
        return render_template("hospital_login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    admin = users.find_one({"email": email, "role": "hospital_admin"})

    if not admin:
        return "Admin not found"

    if not bcrypt.check_password_hash(admin["password"], password):
        return "Wrong password"

    session["hospital_admin"] = str(admin["_id"])
    return redirect("/hospital/dashboard")


@app.route("/hospital/dashboard")
def hospital_dashboard():
    if "hospital_admin" not in session:
        return redirect("/hospital/login")
    return render_template("hospital_dashboard.html")



# =========================================================
# HOSPITAL EXTRA MODULES
# =========================================================

@app.route("/hospital/patient-search", methods=["GET", "POST"])
def hospital_patient_search():
    if "hospital_admin" not in session:
        return redirect("/hospital/login")

    results = []

    if request.method == "POST":
        search_email = request.form.get("email")

        patient = users.find_one({
            "email": search_email,
            "role": "patient"
        })

        if patient:
            results.append(patient)

    return render_template(
        "hospital_patient_search.html",
        results=results
    )

@app.route("/my-appointments")
def my_appointments():

    if session.get("user_role") != "patient":
        return redirect("/select-role")

    patient_id = session.get("user_id")

    patient_appointments = list(appointments.find({
        "patient_id": patient_id
    }).sort("date", 1))

    now = datetime.now() 

    for appt in patient_appointments:
        appt_time = datetime.strptime(
            appt["date"] + " " + appt["time"],
            "%Y-%m-%d %H:%M"
        )

        if now > appt_time:
            appt["status"] = "Completed"
    
    return render_template(
        "patient_appointments.html",
        appointments=patient_appointments
    )

@app.route("/patient/cancel/<appointment_id>", methods=["POST"])
def patient_cancel(appointment_id):

    if session.get("user_role") != "patient":
        return redirect("/select-role")

    appointments.update_one(
        {
            "_id": ObjectId(appointment_id),
            "patient_id": session.get("user_id")
        },
        {"$set": {"status": "Cancelled"}}
    )

    return redirect("/my-appointments")

@app.route("/patient/reschedule/<appointment_id>", methods=["POST"])
def patient_reschedule(appointment_id):

    if session.get("user_role") != "patient":
        return redirect("/select-role")

    appointment = appointments.find_one({
        "_id": ObjectId(appointment_id),
        "patient_id": session.get("user_id")
    })

    if not appointment:
        return redirect("/my-appointments")

    if appointment["status"] != "Confirmed":
        return redirect("/my-appointments")

    doctor_id = appointment["doctor_id"]

    new_date, new_time = generate_next_slot(doctor_id)

    if not new_date:
        return redirect("/my-appointments")

    appointments.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": {
            "date": new_date,
            "time": new_time
        }}
    )

    return redirect("/my-appointments")
# ===============================
# HOSPITAL APPOINTMENTS DASHBOARD
# ===============================

@app.route("/hospital/appointments")
def hospital_appointments():

    if "hospital_admin" not in session:
        return redirect("/hospital/login")

    all_appointments = list(appointments.find().sort("date", 1))

    print("DEBUG APPOINTMENTS:", all_appointments)  
    
    return render_template(
        "hospital_appointments.html",
        appointments=all_appointments
    )
from bson.objectid import ObjectId

@app.route("/book-appointment", methods=["GET", "POST"])
def book_appointment():

    doctors = list(db.users.find({"role": "doctor"}))
    patient = db.users.find_one({"_id": ObjectId(session.get("user_id"))})

    if request.method == "POST":

        doctor_id = request.form.get("doctor_id")
        date = request.form.get("appointment_date")
        time = request.form.get("appointment_time")

        existing_appointment = db.appointments.find_one({
            "doctor_id": doctor_id,
            "date": date,
            "time": time,
            "status": "Confirmed"
        })

        if existing_appointment:
            return render_template(
                "book_appointment.html",
                doctors=doctors,
                error="This time slot is already booked. Please choose another time."
            )

        patient = db.users.find_one({
            "_id": ObjectId(session.get("user_id"))
        })

        doctor = db.users.find_one({"_id": ObjectId(doctor_id)})

        count = db.appointments.count_documents({
            "doctor_id": doctor_id,
            "date": date
        })

        token_number = count + 1

        import uuid
        video_room = "digihealth_" + str(uuid.uuid4())[:8]

        appointment_data = {
            "patient_id": session.get("user_id"),
            "patient_name": patient["name"],
            "doctor_id": doctor_id,
            "doctor_name": doctor["name"],
            "date": date,
            "time": time,
            "token_number": token_number,
            "appointment_type": "video",
            "video_room": video_room,
            "status": "Confirmed",

            "confirmation_sent": False,
            "reminder_1_sent": False,
            "reminder_2_sent": False,
            "completion_email_sent": False,

            "created_at": datetime.now()
        }

        result = db.appointments.insert_one(appointment_data)

        send_confirmation_email(
            patient["email"],
            patient["name"],
            doctor["name"],
            date,
            time
        )

        appointments.update_one(
            {"_id": result.inserted_id},
            {"$set": {"confirmation_sent": True}}
        )

        # ✅ CORRECT PLACE
        return render_template(
            "appointment_success.html",
            doctor=doctor["name"],
            date=date,
            time=time,
            token=token_number
        )

    # ✅ GET REQUEST
    return render_template("book_appointment.html", doctors=doctors)

@app.route("/hospital/cancel-appointment/<appointment_id>", methods=["POST"])
def cancel_appointment(appointment_id):

    if "hospital_admin" not in session:
        return redirect("/hospital/login")

    appointments.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": {"status": "Cancelled"}}
    )

    return redirect("/hospital/appointments")

@app.route("/hospital/reschedule/<appointment_id>", methods=["POST"])
def reschedule_appointment(appointment_id):

    if "hospital_admin" not in session:
        return redirect("/hospital/login")

    appointment = appointments.find_one({
        "_id": ObjectId(appointment_id)
    })

    if not appointment:
        return redirect("/hospital/appointments")

    if appointment["status"] != "Confirmed":
        return redirect("/hospital/appointments")

    doctor_id = appointment["doctor_id"]

    new_date, new_time = generate_next_slot(doctor_id)

    if not new_date or not new_time:
        print("No available slots found.")
        return redirect("/hospital/appointments")

    appointments.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": {
            "date": new_date,
            "time": new_time
        }}
    )

    print("Appointment Rescheduled to:", new_date, new_time)

    return redirect("/hospital/appointments")


@app.route("/hospital/doctors")
def hospital_doctors():
    if "hospital_admin" not in session:
        return redirect("/hospital/login")
    return render_template("hospital_doctors.html")

@app.route("/doctor-availability", methods=["GET", "POST"])
def doctor_availability():

    # 🔐 Protect route
    if session.get("user_role") != "doctor":
        return redirect("/select-role")

    doctor_id = session.get("user_id")


    if request.method == "POST":

        data = {
            "doctor_id": session.get("user_id"),
            "day_of_week": request.form.get("day"),
            "start_time": request.form.get("start_time"),
            "end_time": request.form.get("end_time"),
            "slot_duration": int(request.form.get("duration")),
            "is_active": True,
            "created_at": datetime.now()
        }

        db.doctor_availability.insert_one(data)

        return redirect("/doctor-availability")

    schedules = list(db.doctor_availability.find({
        "doctor_id": session.get("user_id")
    }))

    return render_template("doctor_availability.html", schedules=schedules)


# ===============================
# HOSPITAL - VIEW FULL PATIENT RECORD
# ===============================

@app.route("/hospital/patient/<patient_id>")
def hospital_view_patient(patient_id):

    if "hospital_admin" not in session:
        return redirect("/hospital/login")

    patient = users.find_one({
        "_id": ObjectId(patient_id),
        "role": "patient"
    })

    patient_prescriptions = prescriptions.find({
        "patient_id": patient_id
    })

    return render_template(
        "hospital_patient_record.html",
        patient=patient,
        prescriptions=patient_prescriptions
    )
# ===============================
# HOSPITAL AI - PATIENT LEVEL
# ===============================

@app.route("/hospital/ai-summary/patient/<patient_id>")
def hospital_patient_ai_summary(patient_id):

    if "hospital_admin" not in session:
        return redirect("/hospital/login")

    patient = users.find_one({
        "_id": ObjectId(patient_id),
        "role": "patient"
    })

    if not patient:
        return redirect("/hospital/patient-search")

    patient_prescriptions = list(
        prescriptions.find({"patient_id": patient_id})
    )

    summary_text = f"""
    Patient Name: {patient['name']}
    Email: {patient['email']}
    Prescriptions: {patient_prescriptions}
    """

    ai_response = call_ollama(summary_text)

    return render_template(
        "hospital_patient_ai_summary.html",
        summary=ai_response,
        patient=patient
    )

# ===============================
# HOSPITAL AI - COMMAND CENTER
# ===============================

@app.route("/hospital/ai-summary")
def hospital_ai_dashboard():

    if "hospital_admin" not in session:
        return redirect("/hospital/login")

    appointments_data = list(appointments.find())

    total = len(appointments_data)

    cancelled = len([a for a in appointments_data if a.get("status") == "Cancelled"])
    completed = len([a for a in appointments_data if a.get("status") == "Completed"])

    cancellation_rate = round((cancelled / total) * 100, 2) if total > 0 else 0

    # Doctor utilization
    doctor_count = {}
    for a in appointments_data:
        doctor = a.get("doctor_name", "Unknown")
        doctor_count[doctor] = doctor_count.get(doctor, 0) + 1

    most_active_doctor = max(doctor_count, key=doctor_count.get) if doctor_count else "N/A"

    # Peak hour analysis
    time_count = {}
    for a in appointments_data:
        time = a.get("time", "Unknown")
        time_count[time] = time_count.get(time, 0) + 1

    peak_hour = max(time_count, key=time_count.get) if time_count else "N/A"

    # Risk detection
    alerts = []

    if cancellation_rate > 30:
        alerts.append("High cancellation rate detected.")

    if total > 50:
        alerts.append("High patient load today.")

    if peak_hour != "N/A":
        alerts.append(f"Peak operational time: {peak_hour}")

    if not alerts:
        alerts.append("Operational performance is stable.")

    # Executive Summary Text
    ai_summary = f"""
    Today the hospital managed {total} appointments with a
    {cancellation_rate}% cancellation rate.
    The most active doctor was {most_active_doctor}.
    Peak patient flow occurred at {peak_hour}.
    Operational efficiency is {'stable' if cancellation_rate < 30 else 'needs review'}.
    """

    return render_template(
        "hospital_ai_summary.html",
        total=total,
        cancelled=cancelled,
        completed=completed,
        cancellation_rate=cancellation_rate,
        most_active_doctor=most_active_doctor,
        peak_hour=peak_hour,
        alerts=alerts,
        ai_summary=ai_summary
    )

@app.route('/hospital/availability', methods=['GET', 'POST'])
def manage_availability():

    if 'hospital_admin' not in session:
        return redirect(url_for('hospital_login'))

    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        doctor_name = request.form.get('doctor_name')
        date = request.form['date']
        time_slots = request.form.getlist('time_slots')

        db.doctor_availability.insert_one({
            "doctor_id": doctor_id,
            "doctor_name": doctor_name,
            "date": date,
            "time_slots": time_slots,
            "created_at": datetime.utcnow()
        })

        flash("Availability Added Successfully")

    doctors = list(users.find({"role": "doctor"}))
    availability = list(db.doctor_availability.find())

    return render_template(
        "availability.html",
        doctors=doctors,
        availability=availability
    )

@app.route("/send-demo-email")
def send_demo_email():

    if session.get("user_role") != "patient":
        return jsonify({"message": "Login required"})

    patient = users.find_one({
        "_id": ObjectId(session.get("user_id"))
    })

    send_appointment_email(
        patient["email"],
        patient["name"],
        "Dr Demo",
        "Tomorrow",
        "10:00 AM"
    )

    return jsonify({"message": "Demo email sent!"})
    
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

def send_appointment_email(patient_email, patient_name, doctor_name, date, time):

    message = Mail(
        from_email=SENDER_EMAIL,
        to_emails=patient_email,
        subject="Digi Health Appointment Reminder",
        plain_text_content=f"""
Hello {patient_name},

Reminder: You have a video consultation with Dr. {doctor_name}.

Date: {date}
Time: {time}

Please join through the Digi Health app on time.

Thank you,
Digi Health Team
"""
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        print("Email sent successfully")

    except Exception as e:
        print("Email error:", e)

def send_confirmation_email(patient_email, patient_name, doctor_name, date, time):

    message = Mail(
        from_email=SENDER_EMAIL,
        to_emails=patient_email,
        subject="Appointment Confirmed ✅",
        html_content=f"""
        <div style="font-family: Arial; padding:20px;">
            <h2 style="color:#0b4f6c;">Appointment Confirmed</h2>

            <p>Hello <b>{patient_name}</b>,</p>

            <p>Your appointment with <b>Dr. {doctor_name}</b> has been successfully booked.</p>

            <p>
                <b>Date:</b> {date}<br>
                <b>Time:</b> {time}
            </p>

            <p>We will remind you before your appointment.</p>

            <p style="margin-top:20px;">Digi Health Team</p>
        </div>
        """
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        print("Confirmation email sent")

    except Exception as e:
        print("Email error:", e)

def send_reminder_emails():

    now = datetime.now()

    upcoming_appointments = appointments.find({
        "status": "Confirmed"
    })

    for appt in upcoming_appointments:

        try:
            appointment_time = datetime.strptime(
                appt["date"] + " " + appt["time"],
                "%Y-%m-%d %H:%M"
            )
        except:
            appointment_time = datetime.strptime(
                appt["date"] + " " + appt["time"],
                "%Y-%m-%d %I:%M %p"
            )

        patient = users.find_one({"_id": ObjectId(appt["patient_id"])})

        if not patient:
            continue

        time_diff = (appointment_time - now).total_seconds()
        print("TIME DIFF:", time_diff)

        # ⏰ 1 DAY BEFORE
        if 86000<= time_diff <= 87000 and not appt.get("reminder_1_sent", False):

            send_appointment_email(
                patient["email"],
                patient["name"],
                appt["doctor_name"],
                appt["date"],
                appt["time"]
            )

            appointments.update_one(
                {"_id": appt["_id"]},
                {"$set": {"reminder_1_sent": True}}
            )

        # ⏰ 10 MIN BEFORE
        if 0 <= time_diff <= 600 and not appt.get("reminder_2_sent", False):

            send_appointment_email(
                patient["email"],
                patient["name"],
                appt["doctor_name"],
                appt["date"],
                appt["time"]
            )

            appointments.update_one(
                {"_id": appt["_id"]},
                {"$set": {"reminder_2_sent": True}}
            )

        # ✅ COMPLETED
        if now > appointment_time and appt.get("status") != "Completed":

            appointments.update_one(
                {"_id": appt["_id"]},
                {"$set": {"status": "Completed"}}
            )

            if not appt.get("completion_email_sent", False):

                send_completion_email(
                    patient["email"],
                    patient["name"],
                    appt["doctor_name"],
                    appt["date"],
                    appt["time"]
                )

                appointments.update_one(
                    {"_id": appt["_id"]},
                    {"$set": {"completion_email_sent": True}}
                )
                
def send_completion_email(patient_email, patient_name, doctor_name, date, time):

    message = Mail(
        from_email=SENDER_EMAIL,
        to_emails=patient_email,
        subject="Digi Health - Appointment Completed",
        html_content=f"""
        <div style="font-family: Arial; padding:20px;">
            <h2 style="color:#0b4f6c;">Appointment Completed ✅</h2>

            <p>Hello <b>{patient_name}</b>,</p>

            <p>Your consultation with <b>Dr. {doctor_name}</b> has been completed.</p>

            <p>
                <b>Date:</b> {date}<br>
                <b>Time:</b> {time}
            </p>

            <p>We hope you had a great experience.</p>

            <p style="margin-top:20px;">Stay healthy ❤️<br>Digi Health Team</p>
        </div>
        """
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        print("Completion email sent")

    except Exception as e:
        print("Completion email error:", e)

            
scheduler = BackgroundScheduler()
scheduler.add_job(send_reminder_emails, 'interval', minutes=1)
scheduler.start()

# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    app.run(debug=False)