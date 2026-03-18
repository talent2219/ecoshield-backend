"""
Run this once to populate your database with test data:
    python seed.py
"""
from app import create_app
from database import db
from models import User, Transaction, Alert
from werkzeug.security import generate_password_hash
from utils.fraud_engine import score_transaction, auto_action
from datetime import datetime, timedelta
import random
import string

app = create_app()

NAMES    = ["Tendai Moyo", "Rudo Chikwanda", "Farai Ncube", "Chipo Kumalo", "Tatenda Gomo",
            "Blessing Zuva", "Simba Wekwa", "Nyasha Tafara", "Gift Muropa", "Vimbai Sithole"]
PHONES   = [f"+26377{random.randint(1000000,9999999)}" for _ in range(10)]
PLATFORMS = ["EcoCash", "OneMoney", "Telecash"]
TYPES     = ["send", "receive", "withdraw", "payment"]

def gen_ref():
    return "TX-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))

with app.app_context():
    db.drop_all()
    db.create_all()

    # ── Create users ────────────────────────────────────────────────────────
    users = []
    for i, name in enumerate(NAMES):
        u = User(
            name          = name,
            phone         = f"+2637712{i:05d}",
            platform      = random.choice(PLATFORMS),
            password_hash = generate_password_hash("password123"),
            is_admin      = (i == 0),  # First user is admin
        )
        db.session.add(u)
        users.append(u)

    db.session.commit()
    print(f"Created {len(users)} users")

    # ── Create transactions ──────────────────────────────────────────────────
    txs = []
    for _ in range(80):
        user   = random.choice(users)
        amount = round(random.uniform(50, 9500), 2)
        hour   = random.randint(0, 23)
        new_r  = random.random() < 0.3
        for_ip = random.random() < 0.08
        rapid  = random.random() < 0.12

        result = score_transaction({
            "user_id":      user.id,
            "amount":       amount,
            "hour":         hour,
            "is_new_recip": new_r,
            "foreign_ip":   for_ip,
            "tx_type":      random.choice(TYPES),
        })
        status = auto_action(result["fraud_score"], result["risk_level"])

        # Spread over last 7 days
        days_ago = random.randint(0, 6)
        created  = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0,23))

        tx = Transaction(
            tx_ref        = gen_ref(),
            user_id       = user.id,
            tx_type       = random.choice(TYPES),
            amount        = amount,
            recipient     = f"+2637{random.randint(10000000,99999999)}",
            platform      = user.platform,
            hour          = hour,
            is_new_recip  = new_r,
            is_rapid_fire = rapid,
            foreign_ip    = for_ip,
            fraud_score   = result["fraud_score"],
            risk_level    = result["risk_level"],
            status        = status,
            created_at    = created,
        )
        db.session.add(tx)
        txs.append(tx)

    db.session.commit()
    print(f"Created {len(txs)} transactions")

    # ── Create alerts for high-risk transactions ──────────────────────────
    alert_count = 0
    for tx in txs:
        if tx.risk_level == "high":
            alert = Alert(
                user_id        = tx.user_id,
                transaction_id = tx.id,
                alert_type     = "fraud",
                severity       = "high",
                title          = "Suspicious transaction detected",
                message        = f"A ${tx.amount:,.0f} {tx.tx_type} scored {tx.fraud_score:.0f}/99 and was {tx.status}.",
                created_at     = tx.created_at,
            )
            db.session.add(alert)
            alert_count += 1

    db.session.commit()
    print(f"Created {alert_count} alerts")
    print("\nDone! Test credentials:")
    print("  Admin: phone=+263771200000  password=password123")
    print("  User:  phone=+263771200001  password=password123")
