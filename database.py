import json
import os
from typing import Optional

DB_FILE = os.environ.get("DB_PATH", "students.json")


def load_db() -> dict:
    if not os.path.exists(DB_FILE):
        data = {"students": []}
        save_db(data)
        return data
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(data: dict):
    os.makedirs(os.path.dirname(DB_FILE) if os.path.dirname(DB_FILE) else ".", exist_ok=True)
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_all_students() -> list:
    return load_db()["students"]


def add_student(fio: str, login: str, password: str,
                parent_login: str, parent_password: str) -> bool:
    db = load_db()
    # Duplicate login check
    for s in db["students"]:
        if s["login"] == login:
            return False
    db["students"].append({
        "fio": fio,
        "login": login,
        "password": password,
        "parent": {
            "login": parent_login,
            "password": parent_password
        }
    })
    save_db(db)
    return True


def delete_student(login: str) -> bool:
    db = load_db()
    before = len(db["students"])
    db["students"] = [s for s in db["students"] if s["login"] != login]
    if len(db["students"]) < before:
        save_db(db)
        return True
    return False


def update_student(login: str, field: str, value: str) -> bool:
    """
    field: 'fio' | 'login' | 'password' | 'parent_login' | 'parent_password'
    """
    db = load_db()
    for s in db["students"]:
        if s["login"] == login:
            if field == "fio":
                s["fio"] = value
            elif field == "password":
                s["password"] = value
            elif field == "parent_login":
                s["parent"]["login"] = value
            elif field == "parent_password":
                s["parent"]["password"] = value
            save_db(db)
            return True
    return False


def get_student(login: str) -> Optional[dict]:
    for s in get_all_students():
        if s["login"] == login:
            return s
    return None
