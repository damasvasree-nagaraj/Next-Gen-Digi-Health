import uuid

video_room = None

if appointment_type == "video":
    video_room = "digihealth_" + str(uuid.uuid4())[:8]

appointment_data = {
    "doctor_id": doctor_id,
    "patient_id": patient_id,
    "date": date,
    "time": time,
    "appointment_type": appointment_type,
    "video_room": video_room,
    "status": "pending"
}