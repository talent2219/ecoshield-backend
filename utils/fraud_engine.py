"""
EcoShield Fraud Scoring Engine — ML Version
---------------------------------------------
Uses a trained Random Forest model (model.pkl) to score transactions.
"""

import os
import joblib
import numpy as np
from datetime import datetime, timedelta

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'model.pkl')

try:
    model = joblib.load(MODEL_PATH)
    print("ML model loaded successfully!")
except Exception as e:
    print(f"Warning: Could not load ML model: {e}")
    model = None


def _rapid_fire_risk(user_id: int) -> bool:
    try:
        from database import db
        from models import Transaction
        five_min_ago = datetime.utcnow() - timedelta(minutes=5)
        recent_count = Transaction.query.filter(Transaction.user_id == user_id, Transaction.created_at >= five_min_ago).count()
        return recent_count >= 3
    except Exception:
        return False


def score_transaction(tx_data: dict) -> dict:
    rapid = _rapid_fire_risk(tx_data.get("user_id", 0))
    type_map = {"send": 0, "receive": 1, "withdraw": 2, "payment": 3}
    tx_type_num = type_map.get(tx_data.get("tx_type", "send"), 0)
    features = [[
        float(tx_data.get("amount", 0)),
        int(tx_data.get("hour", datetime.utcnow().hour)),
        int(tx_data.get("is_new_recip", False)),
        int(rapid),
        int(tx_data.get("foreign_ip", False)),
        tx_type_num,
    ]]
    if model is not None:
        fraud_prob = model.predict_proba(features)[0][1]
        fraud_score = min(int(fraud_prob * 99), 99)
    else:
        score = 0
        a = 70 if tx_data.get("amount", 0) > 8000 else 40 if tx_data.get("amount", 0) > 4000 else 10
        score += a * 0.3
        t = 80 if (tx_data.get("hour", 12) >= 23 or tx_data.get("hour", 12) <= 5) else 5
        score += t * 0.25
        score += (75 if tx_data.get("is_new_recip") else 10) * 0.2
        score += (85 if rapid else 15) * 0.15
        score += (90 if tx_data.get("foreign_ip") else 5) * 0.1
        fraud_score = min(int(score), 99)
    risk_level = "high" if fraud_score >= 65 else "medium" if fraud_score >= 35 else "low"
    signals = {
        "Unusual amount":     70 if tx_data.get("amount", 0) > 4000 else 10,
        "Off-hours":          80 if (tx_data.get("hour", 12) >= 23 or tx_data.get("hour", 12) <= 5) else 5,
        "New recipient":      75 if tx_data.get("is_new_recip") else 10,
        "Rapid transactions": 85 if rapid else 15,
        "Location mismatch":  90 if tx_data.get("foreign_ip") else 5,
    }
    return {"fraud_score": fraud_score, "risk_level": risk_level, "signals": signals, "is_rapid": rapid}


def auto_action(fraud_score: int, risk_level: str) -> str:
    if fraud_score >= 80: return "blocked"
    if risk_level == "high": return "flagged"
    return "clear"
