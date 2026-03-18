from flask import Blueprint, request, jsonify
from database import db
from models import Transaction, Alert, User
from utils.fraud_engine import score_transaction, auto_action
from datetime import datetime
import random
import string

transactions_bp = Blueprint("transactions", __name__)


def gen_ref():
    """Generate a unique transaction reference like TX-A9F21."""
    return "TX-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))


def create_alert_for_transaction(tx: Transaction):
    """Automatically create an alert if transaction is flagged or blocked."""
    if tx.risk_level == "low":
        return  # No alert needed for low-risk

    title_map = {
        "high":   f"Suspicious transaction {'blocked' if tx.status == 'blocked' else 'flagged'}",
        "medium": "Transaction flagged for review",
    }
    msg_map = {
        "high":   f"A ${tx.amount:,.0f} {tx.tx_type} to {tx.recipient or 'unknown'} scored {tx.fraud_score:.0f}/99 on our fraud detector and was {tx.status}.",
        "medium": f"A ${tx.amount:,.0f} {tx.tx_type} has been flagged for review with a fraud score of {tx.fraud_score:.0f}/99.",
    }
    severity_map = {"high": "high", "medium": "medium"}

    alert = Alert(
        user_id        = tx.user_id,
        transaction_id = tx.id,
        alert_type     = "fraud",
        severity       = severity_map[tx.risk_level],
        title          = title_map[tx.risk_level],
        message        = msg_map[tx.risk_level],
    )
    db.session.add(alert)
    db.session.commit()


# ── POST /api/transactions/submit ─────────────────────────────────────────
@transactions_bp.route("/submit", methods=["POST"])
def submit():
    """
    Submit a new transaction for fraud scoring.

    Body (JSON):
        user_id, tx_type, amount, recipient, platform,
        is_new_recip (bool), foreign_ip (bool)
    """
    data = request.get_json()

    required = ["user_id", "tx_type", "amount", "platform"]
    for field in required:
        if not data.get(field) and data.get(field) != 0:
            return jsonify({"error": f"'{field}' is required"}), 400

    hour = datetime.utcnow().hour

    # Score the transaction
    result = score_transaction({
        "user_id":      data["user_id"],
        "amount":       float(data["amount"]),
        "hour":         hour,
        "is_new_recip": data.get("is_new_recip", False),
        "foreign_ip":   data.get("foreign_ip", False),
        "tx_type":      data["tx_type"],
    })

    status = auto_action(result["fraud_score"], result["risk_level"])

    tx = Transaction(
        tx_ref        = gen_ref(),
        user_id       = data["user_id"],
        tx_type       = data["tx_type"],
        amount        = float(data["amount"]),
        recipient     = data.get("recipient", ""),
        platform      = data["platform"],
        hour          = hour,
        is_new_recip  = data.get("is_new_recip", False),
        is_rapid_fire = result["is_rapid"],
        foreign_ip    = data.get("foreign_ip", False),
        fraud_score   = result["fraud_score"],
        risk_level    = result["risk_level"],
        status        = status,
    )
    db.session.add(tx)
    db.session.commit()

    # Create alert if needed
    create_alert_for_transaction(tx)

    return jsonify({
        "transaction": tx.to_dict(),
        "fraud_score": result["fraud_score"],
        "risk_level":  result["risk_level"],
        "status":      status,
        "signals":     result["signals"],
        "message":     f"Transaction {status}." if status != "clear" else "Transaction approved.",
    }), 201


# ── GET /api/transactions ─────────────────────────────────────────────────
@transactions_bp.route("/", methods=["GET"])
def list_transactions():
    """
    Query params:
        user_id   — filter by user
        risk      — filter by risk_level (low|medium|high)
        status    — filter by status (clear|flagged|blocked)
        limit     — max results (default 50)
    """
    query = Transaction.query

    user_id = request.args.get("user_id")
    risk    = request.args.get("risk")
    status  = request.args.get("status")
    limit   = int(request.args.get("limit", 50))

    if user_id: query = query.filter_by(user_id=int(user_id))
    if risk:    query = query.filter_by(risk_level=risk)
    if status:  query = query.filter_by(status=status)

    txs = query.order_by(Transaction.created_at.desc()).limit(limit).all()
    return jsonify([t.to_dict() for t in txs]), 200


# ── GET /api/transactions/<id> ────────────────────────────────────────────
@transactions_bp.route("/<int:tx_id>", methods=["GET"])
def get_transaction(tx_id):
    tx = Transaction.query.get_or_404(tx_id)
    return jsonify(tx.to_dict()), 200


# ── PATCH /api/transactions/<id>/action ──────────────────────────────────
@transactions_bp.route("/<int:tx_id>/action", methods=["PATCH"])
def take_action(tx_id):
    """
    Manually update a transaction status.
    Body: { "action": "blocked" | "flagged" | "clear" }
    """
    tx     = Transaction.query.get_or_404(tx_id)
    action = request.get_json().get("action")

    if action not in ("blocked", "flagged", "clear"):
        return jsonify({"error": "action must be blocked | flagged | clear"}), 400

    tx.status = action
    db.session.commit()
    return jsonify({"message": f"Transaction {action}.", "transaction": tx.to_dict()}), 200
