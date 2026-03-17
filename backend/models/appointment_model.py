import uuid

def generate_video_room():
    return "digihealth_" + str(uuid.uuid4())[:8]

appointment = {
    "doctor_id": doctor_id,
    "patient_id": patient_id,
    "date": date,
    "time": time,
    "appointment_type": appointment_type,
    "video_room": generate_video_room() if appointment_type == "video" else None,
    "status": "pending"
}