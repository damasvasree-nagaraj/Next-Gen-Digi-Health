from flask import Flask, request, jsonify, render_template, redirect, session, url_for, flash
from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from urllib.parse import quote_plus
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from flask import send_file
from io import BytesIO
from reportlab.pdfgen import canvas
import random
import certifi
import requests

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
app.secret_key = "nextgen_digi_health_secret_key"
bcrypt = Bcrypt(app)

# ================= DATABASE =================
MONGO_USERNAME=nextgen_admin
MONGO_PASSWORD=nextgen123

MONGO_URI = (
    f"mongodb+srv://{username}:{password}"
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

# ================= AI IMPORTS =================
from ai_chatbot.ollama_client import call_ollama
from ai_chatbot.rag_engine import retrieve_context
from ai_chatbot.prompts import SYSTEM_PROMPT, build_user_prompt


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

    if not user_message:
        return jsonify({"reply": "Please enter a message."})

    try:
        context = retrieve_context(user_message)
        prompt = SYSTEM_PROMPT + build_user_prompt(context, user_message)
        reply = call_ollama(prompt)

        return jsonify({"reply": reply})

    except Exception as e:
        print("Chat Error:", e)
        return jsonify({"reply": "AI temporarily unavailable."})


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
        "date": today
    }).sort("time", 1))

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

    claims = list(db.insurance_claims.find({
        "doctor_id": doctor_id
    }))

    return render_template(
        "doctor_claims.html",
        claims=claims
    )
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

        # 🔴 Check if slot already booked
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

        # 🔵 Generate daily token number per doctor
        count = db.appointments.count_documents({
            "doctor_id": doctor_id,
            "date": date
        })

        token_number = count + 1

        appointment_data = {
            "patient_id": session.get("user_id"),
            "patient_name": patient["name"],
            "doctor_id": doctor_id,
            "doctor_name": doctor["name"],
            "date": date,
            "time": time,
            "token_number": token_number,
            "status": "Confirmed",
            "created_at": datetime.now()
        }

        db.appointments.insert_one(appointment_data)

        return render_template(
            "appointment_success.html",
            doctor=doctor["name"],
            date=date,
            time=time,
            token=token_number
        )

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


# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    app.run(debug=True)