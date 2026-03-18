from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from database import db
from models import User

auth_bp = Blueprint("auth", __name__)
SECRET = "ecoshield-secret-change-in-production"


def make_token(user_id: int, is_admin: bool) -> str:
    payload = {
        "user_id":  user_id,
        "is_admin": is_admin,
        "exp":      datetime.datetime.utcnow() + datetime.timedelta(hours=24),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


# ── POST /api/auth/register ───────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    required = ["name", "phone", "platform", "password"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"'{field}' is required"}), 400

    if User.query.filter_by(phone=data["phone"]).first():
        return jsonify({"error": "Phone number already registered"}), 409

    user = User(
        name          = data["name"],
        phone         = data["phone"],
        platform      = data["platform"],
        password_hash = generate_password_hash(data["password"]),
    )
    db.session.add(user)
    db.session.commit()

    token = make_token(user.id, user.is_admin)
    return jsonify({"token": token, "user": user.to_dict()}), 201


# ── POST /api/auth/login ──────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = User.query.filter_by(phone=data.get("phone")).first()

    if not user or not check_password_hash(user.password_hash, data.get("password", "")):
        return jsonify({"error": "Invalid phone or password"}), 401

    token = make_token(user.id, user.is_admin)
    return jsonify({"token": token, "user": user.to_dict()}), 200


# ── GET /api/auth/me ──────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
def me():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
        user    = User.query.get(payload["user_id"])
        return jsonify(user.to_dict()), 200
    except Exception:
        return jsonify({"error": "Invalid or expired token"}), 401
