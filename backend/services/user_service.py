from config.db import db

def register_user(name, email, password, role):
    user = {
        "name": name,
        "email": email,
        "password": password,
        "role": role
    }
    return db.users.insert_one(user)


def find_user_by_email(email):
    return db.users.find_one({"email": email})