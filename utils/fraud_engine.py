"""
EcoShield Fraud Scoring Engine - Pure Python Version
------------------------------------------------------
Uses model_data.json (exported from trained Random Forest)
No scikit-learn needed - works on any server!
"""

import os
import json
from datetime import datetime, timedelta

# Load the model data once when server starts
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'model_data.json')

try:
    with open(MODEL_PATH, 'r') as f:
        TREES = json.load(f)
    print(f"ML model loaded successfully! ({len(TREES)} trees)")
except Exception as e:
    print(f"Warning: Could not load ML model: {e}")
    TREES = None


def _predict_one_tree(tree, features):
    """Walk one decision tree and return fraud probability."""
    node = 0
    while tree['children_left'][node] != -1:
        feat_idx = tree['feature'][node]
        threshold = tree['threshold'][node]
        if features[feat_idx] <= threshold:
            node = tree['children_left'][node]
        else:
            node = tree['children_right'][node]
    # value shape is [n_samples, n_classes] — get fraud class (index 1)
    value = tree['value'][node][0]
    total = sum(value)
    return value[1] / total if total > 0 else 0.0


def _ml_score(features: list) -> float:
    """Average fraud probability across all 100 trees."""
    if not TREES:
        return 0.0
    probs = [_predict_one_tree(tree, features) for tree in TREES]
    return sum(probs) / len(probs)


def _rapid_fire_risk(user_id: int) -> bool:
    """True if user made 3+ transactions in the last 5 minutes."""
    try:
        from models import Transaction
        five_min_ago = datetime.utcnow() - timedelta(minutes=5)
        count = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.created_at >= five_min_ago
        ).count()
        return count >= 3
    except Exception:
        return False


def score_transaction(tx_data: dict) -> dict:
    """Score a transaction and return fraud_score, risk_level and signals."""
    rapid = _rapid_fire_risk(tx_data.get("user_id", 0))

    type_map = {"send": 0, "receive": 1, "withdraw": 2, "payment": 3}
    tx_type_num = type_map.get(tx_data.get("tx_type", "send"), 0)

    features = [
        float(tx_data.get("amount", 0)),
        int(tx_data.get("hour", datetime.utcnow().hour)),
        int(tx_data.get("is_new_recip", False)),
        int(rapid),
        int(tx_data.get("foreign_ip", False)),
        tx_type_num,
    ]

    if TREES:
        fraud_prob  = _ml_score(features)
        fraud_score = min(int(fraud_prob * 99), 99)
    else:
        # Fallback rule-based scoring
        score = 0
        a = 70 if features[0] > 8000 else 40 if features[0] > 4000 else 10
        score += a * 0.30
        t = 80 if (features[1] >= 23 or features[1] <= 5) else 5
        score += t * 0.25
        score += (75 if features[2] else 10) * 0.20
        score += (85 if features[3] else 15) * 0.15
        score += (90 if features[4] else 5)  * 0.10
        fraud_score = min(int(score), 99)

    risk_level = (
        "high"   if fraud_score >= 65 else
        "medium" if fraud_score >= 35 else
        "low"
    )

    signals = {
        "Unusual amount":     70 if features[0] > 4000 else 10,
        "Off-hours":          80 if (features[1] >= 23 or features[1] <= 5) else 5,
        "New recipient":      75 if features[2] else 10,
        "Rapid transactions": 85 if rapid else 15,
        "Location mismatch":  90 if features[4] else 5,
    }

    return {
        "fraud_score": fraud_score,
        "risk_level":  risk_level,
        "signals":     signals,
        "is_rapid":    rapid,
    }


def auto_action(fraud_score: int, risk_level: str) -> str:
    """Decide what to do automatically based on risk score."""
    if fraud_score >= 80:    return "blocked"
    if risk_level == "high": return "flagged"
    return "clear"
