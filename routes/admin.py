from flask import Blueprint, request, jsonify
from database import db
from models import Transaction, Alert, User
from sqlalchemy import func
from datetime import datetime, timedelta

admin_bp = Blueprint("admin", __name__)


# ── GET /api/admin/stats ──────────────────────────────────────────────────
@admin_bp.route("/stats", methods=["GET"])
def stats():
    """Overall fraud statistics for the admin dashboard."""
    since = datetime.utcnow() - timedelta(days=7)

    total      = Transaction.query.filter(Transaction.created_at >= since).count()
    flagged    = Transaction.query.filter(Transaction.created_at >= since, Transaction.risk_level == "high").count()
    blocked    = Transaction.query.filter(Transaction.created_at >= since, Transaction.status == "blocked").count()

    # Total amount blocked (saved from fraud)
    amount_row = (
        db.session.query(func.sum(Transaction.amount))
        .filter(Transaction.created_at >= since, Transaction.status == "blocked")
        .scalar()
    )
    amount_blocked = round(amount_row or 0, 2)

    # False positive rate: flagged but later cleared
    cleared_after_flag = Transaction.query.filter(
        Transaction.created_at >= since,
        Transaction.risk_level == "high",
        Transaction.status == "clear"
    ).count()
    fp_rate = round((cleared_after_flag / flagged * 100), 1) if flagged > 0 else 0.0

    return jsonify({
        "period_days":    7,
        "total":          total,
        "flagged":        flagged,
        "blocked":        blocked,
        "amount_blocked": amount_blocked,
        "false_positive": fp_rate,
        "accuracy":       round(100 - fp_rate, 1),
    }), 200


# ── GET /api/admin/cases ──────────────────────────────────────────────────
@admin_bp.route("/cases", methods=["GET"])
def cases():
    """All high-risk and flagged transactions as open cases."""
    txs = (
        Transaction.query
        .filter(Transaction.risk_level.in_(["high", "medium"]))
        .order_by(Transaction.created_at.desc())
        .limit(50)
        .all()
    )
    return jsonify([t.to_dict() for t in txs]), 200


# ── GET /api/admin/users ──────────────────────────────────────────────────
@admin_bp.route("/users", methods=["GET"])
def users():
    """All users sorted by risk score descending."""
    all_users = User.query.order_by(User.risk_score.desc()).all()
    return jsonify([u.to_dict() for u in all_users]), 200


# ── PATCH /api/admin/users/<id>/freeze ───────────────────────────────────
@admin_bp.route("/users/<int:user_id>/freeze", methods=["PATCH"])
def freeze_user(user_id):
    """Freeze or unfreeze a user account."""
    user = User.query.get_or_404(user_id)
    user.is_frozen = not user.is_frozen
    db.session.commit()
    state = "frozen" if user.is_frozen else "unfrozen"
    return jsonify({"message": f"Account {state}.", "user": user.to_dict()}), 200


# ── GET /api/admin/fraud-by-type ─────────────────────────────────────────
@admin_bp.route("/fraud-by-type", methods=["GET"])
def fraud_by_type():
    """Count of high-risk transactions grouped by tx_type."""
    rows = (
        db.session.query(Transaction.tx_type, func.count(Transaction.id))
        .filter(Transaction.risk_level == "high")
        .group_by(Transaction.tx_type)
        .all()
    )
    return jsonify({row[0]: row[1] for row in rows}), 200


# ── GET /api/admin/daily-trend ────────────────────────────────────────────
@admin_bp.route("/daily-trend", methods=["GET"])
def daily_trend():
    """Average fraud score per day for the last 7 days."""
    results = []
    for i in range(6, -1, -1):
        day_start = datetime.utcnow().replace(hour=0, minute=0, second=0) - timedelta(days=i)
        day_end   = day_start + timedelta(days=1)
        avg = (
            db.session.query(func.avg(Transaction.fraud_score))
            .filter(Transaction.created_at >= day_start, Transaction.created_at < day_end)
            .scalar()
        )
        results.append({
            "date":      day_start.strftime("%a"),
            "avg_score": round(avg or 0, 1),
        })
    return jsonify(results), 200
