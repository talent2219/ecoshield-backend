"""
EcoShield Fraud Scoring Engine - ML Version
---------------------------------------------
Uses a trained Random Forest model to score transactions.
"""

import joblib
import os
from datetime import datetime, timedelta

# Load the trained model
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'model.pkl')

try:
    model = joblib.load(MODEL_PATH)
    print("ML model loaded successfully!")
except Exception as e:
    print(f"Warning: Could not load ML model ({e}). Using rule-based scoring.")
    model = None


def _rapid_fire_risk(user_id: int) -> bool:
    """True if the user made 3+ transactions in the last 5 minutes."""
    try:
        from models import Transaction
        from database import db
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
    except Exception:
        return False


def score_transaction(tx_data: dict) -> dict:
    """
    Score a transaction using the trained ML model.
    Falls back to rule-based scoring if model is not available.
    """
    rapid = _rapid_fire_risk(tx_data.get("user_id", 0))

    # Map tx_type to number
    tx_type_map = {"send": 0, "receive": 1, "withdraw": 2, "payment": 3}
    tx_type_num = tx_type_map.get(tx_data.get("tx_type", "send"), 0)

    features = [[
        float(tx_data.get("amount", 0)),
        int(tx_data.get("hour", datetime.utcnow().hour)),
        int(tx_data.get("is_new_recip", False)),
        int(rapid),
        int(tx_data.get("foreign_ip", False)),
        tx_type_num,
    ]]

    if model is not None:
        # Use ML model
        fraud_prob  = model.predict_proba(features)[0][1]
        fraud_score = min(int(fraud_prob * 99), 99)
        signals = {
            "unusual_amount":    int(float(tx_data.get("amount", 0)) / 100),
            "off_hours":         80 if (int(tx_data.get("hour", 12)) >= 23 or int(tx_data.get("hour", 12)) <= 5) else 5,
            "new_recipient":     75 if tx_data.get("is_new_recip") else 10,
            "rapid_transactions":85 if rapid else 15,
            "location_mismatch": 90 if tx_data.get("foreign_ip") else 5,
        }
    else:
        # Fallback rule-based scoring
        s = 0
        signals = {}
        a = 70 if float(tx_data.get("amount", 0)) > 8000 else 40 if float(tx_data.get("amount", 0)) > 4000 else 10
        s += a * 0.30; signals["unusual_amount"] = a
        h = int(tx_data.get("hour", 12))
        t = 80 if (h >= 23 or h <= 5) else 40 if (h >= 21 or h <= 7) else 5
        s += t * 0.25; signals["off_hours"] = t
        n = 75 if tx_data.get("is_new_recip") else 10
        s += n * 0.20; signals["new_recipient"] = n
        r = 85 if rapid else 15
        s += r * 0.15; signals["rapid_transactions"] = r
        l = 90 if tx_data.get("foreign_ip") else 5
        s += l * 0.10; signals["location_mismatch"] = l
        fraud_score = min(int(s), 99)

    risk_level = (
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
    """Decide what to do automatically based on risk."""
    if fraud_score >= 80:    return "blocked"
    if risk_level == "high": return "flagged"
    return "clear"
