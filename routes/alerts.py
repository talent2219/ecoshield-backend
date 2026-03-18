from flask import Blueprint, request, jsonify
from database import db
from models import Alert

alerts_bp = Blueprint("alerts", __name__)


# ── GET /api/alerts ───────────────────────────────────────────────────────
@alerts_bp.route("/", methods=["GET"])
def list_alerts():
    """
    Query params:
        user_id  — filter by user (required)
        unread   — if "true", return only unread alerts
    """
    user_id = request.args.get("user_id")
    unread  = request.args.get("unread", "false").lower() == "true"

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    query = Alert.query.filter_by(user_id=int(user_id))
    if unread:
        query = query.filter_by(is_read=False)

    alerts = query.order_by(Alert.created_at.desc()).limit(20).all()
    return jsonify([a.to_dict() for a in alerts]), 200


# ── PATCH /api/alerts/<id>/read ───────────────────────────────────────────
@alerts_bp.route("/<int:alert_id>/read", methods=["PATCH"])
def mark_read(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    alert.is_read = True
    db.session.commit()
    return jsonify({"message": "Alert marked as read."}), 200


# ── PATCH /api/alerts/<id>/action ─────────────────────────────────────────
@alerts_bp.route("/<int:alert_id>/action", methods=["PATCH"])
def take_action(alert_id):
    """
    Body: { "action": "confirmed" | "dismissed" | "blocked" }
    """
    alert  = Alert.query.get_or_404(alert_id)
    action = request.get_json().get("action")

    if action not in ("confirmed", "dismissed", "blocked"):
        return jsonify({"error": "Invalid action"}), 400

    alert.action_taken = action
    alert.is_read      = True
    db.session.commit()
    return jsonify({"message": f"Alert {action}.", "alert": alert.to_dict()}), 200


# ── GET /api/alerts/unread-count ──────────────────────────────────────────
@alerts_bp.route("/unread-count", methods=["GET"])
def unread_count():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    count = Alert.query.filter_by(user_id=int(user_id), is_read=False).count()
    return jsonify({"unread": count}), 200
