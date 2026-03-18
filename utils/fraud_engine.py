"""
EcoShield Fraud Scoring Engine
-------------------------------
This module scores every transaction for fraud risk.

Right now it uses a rule-based weighted model.
In Step 4 you will swap score_transaction() to call
your trained Random Forest / XGBoost model instead.
"""

import random
from datetime import datetime, timedelta
from database import db


# ── Weights (must sum to 1.0) ──────────────────────────────────────────────
WEIGHTS = {
    "amount":      0.30,
    "time":        0.25,
    "new_recip":   0.20,
    "rapid_fire":  0.15,
    "location":    0.10,
}


def _amount_risk(amount: float) -> int:
    """Higher amounts = higher risk."""
    if amount > 8_000:  return 70
    if amount > 4_000:  return 40
    if amount > 1_000:  return 20
    return 10


def _time_risk(hour: int) -> int:
    """Late-night and early-morning transactions are riskier."""
    if hour >= 23 or hour <= 5:  return 80
    if hour >= 21 or hour <= 7:  return 40
    return 5


def _rapid_fire_risk(user_id: int) -> bool:
    """True if the user made 3+ transactions in the last 5 minutes."""
    from models import Transaction
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    recent_count = (
        Transaction.query
        .filter(
            Transaction.user_id == user_id,
            Transaction.created_at >= five_min_ago
        )
        .count()
    )
    return recent_count >= 3


def score_transaction(tx_data: dict) -> dict:
    """
    Score a transaction dict and return fraud_score + risk_level + signals.

    tx_data keys expected:
        user_id, amount, hour, is_new_recip, foreign_ip, tx_type
    """
    signals = {}
    total   = 0.0

    # 1. Amount risk
    a = _amount_risk(tx_data.get("amount", 0))
    signals["unusual_amount"] = a
    total += a * WEIGHTS["amount"]

    # 2. Time-of-day risk
    t = _time_risk(tx_data.get("hour", datetime.utcnow().hour))
    signals["off_hours"] = t
    total += t * WEIGHTS["time"]

    # 3. New recipient
    n = 75 if tx_data.get("is_new_recip", False) else 10
    signals["new_recipient"] = n
    total += n * WEIGHTS["new_recip"]

    # 4. Rapid-fire transactions
    rapid = _rapid_fire_risk(tx_data.get("user_id", 0))
    r = 85 if rapid else 15
    signals["rapid_transactions"] = r
    total += r * WEIGHTS["rapid_fire"]

    # 5. Foreign / unusual IP location
    l = 90 if tx_data.get("foreign_ip", False) else 5
    signals["location_mismatch"] = l
    total += l * WEIGHTS["location"]

    fraud_score = min(round(total), 99)
    risk_level  = (
        "high"   if fraud_score >= 65 else
        "medium" if fraud_score >= 35 else
        "low"
    )

    return {
        "fraud_score": fraud_score,
        "risk_level":  risk_level,
        "signals":     signals,
        "is_rapid":    rapid,
    }


def auto_action(fraud_score: int, risk_level: str) -> str:
    """
    Decide what to do automatically based on risk.
    Returns: 'blocked' | 'flagged' | 'clear'
    """
    if fraud_score >= 80:  return "blocked"
    if risk_level == "high": return "flagged"
    return "clear"
