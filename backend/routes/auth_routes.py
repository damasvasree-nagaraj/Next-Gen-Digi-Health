from flask import Blueprint, request, redirect, session
from services.user_service import register_user, find_user_by_email

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    role = request.form["role"]

    register_user(name, email, password, role)
    return redirect("/login")


@auth_bp.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    user = find_user_by_email(email)

    if user and user["password"] == password:
        session["user_id"] = str(user["_id"])
        session["user_role"] = user["role"]

        if user["role"] == "doctor":
            return redirect("/doctor/dashboard")
        else:
            return redirect("/patient/dashboard")

    return "Invalid login"