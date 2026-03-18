# EcoShield — Python Backend

Real-time mobile money fraud detection API built with Flask.

---

## Project structure

```
ecoshield/
├── app.py                  ← Entry point — run this to start the server
├── database.py             ← SQLAlchemy setup
├── models.py               ← Database tables (User, Transaction, Alert)
├── seed.py                 ← Populate database with test data
├── requirements.txt        ← Python packages needed
├── routes/
│   ├── auth.py             ← Register, login, /me
│   ├── transactions.py     ← Submit & score transactions
│   ├── alerts.py           ← Read & action alerts
│   └── admin.py            ← Stats, cases, user management
└── utils/
    └── fraud_engine.py     ← Fraud scoring logic (swap for ML model in Step 4)
```

---

## Setup (do this once)

**1. Install Python 3.10+** from https://python.org

**2. Open a terminal in this folder and create a virtual environment:**
```bash
python -m venv venv
```

**3. Activate it:**
- Windows:  `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

**4. Install packages:**
```bash
pip install -r requirements.txt
```

**5. Seed the database with test data:**
```bash
python seed.py
```

**6. Start the server:**
```bash
python app.py
```

Server runs at: http://localhost:5000

---

## API endpoints

### Auth
| Method | URL | What it does |
|--------|-----|-------------|
| POST | /api/auth/register | Create new account |
| POST | /api/auth/login | Login, get JWT token |
| GET  | /api/auth/me | Get current user info |

### Transactions
| Method | URL | What it does |
|--------|-----|-------------|
| POST  | /api/transactions/submit | Submit transaction for fraud scoring |
| GET   | /api/transactions/ | List all transactions |
| GET   | /api/transactions/<id> | Get one transaction |
| PATCH | /api/transactions/<id>/action | Block / flag / clear |

### Alerts
| Method | URL | What it does |
|--------|-----|-------------|
| GET   | /api/alerts/?user_id=1 | Get user's alerts |
| PATCH | /api/alerts/<id>/read | Mark alert as read |
| PATCH | /api/alerts/<id>/action | Confirm / dismiss / block |
| GET   | /api/alerts/unread-count?user_id=1 | Count unread alerts |

### Admin
| Method | URL | What it does |
|--------|-----|-------------|
| GET   | /api/admin/stats | Overall fraud stats (7 days) |
| GET   | /api/admin/cases | All flagged/blocked transactions |
| GET   | /api/admin/users | All users sorted by risk score |
| PATCH | /api/admin/users/<id>/freeze | Freeze/unfreeze account |
| GET   | /api/admin/fraud-by-type | Fraud count grouped by type |
| GET   | /api/admin/daily-trend | Average fraud score per day |

---

## Example: Submit a transaction

```bash
curl -X POST http://localhost:5000/api/transactions/submit \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "tx_type": "send",
    "amount": 4500,
    "recipient": "+263771999888",
    "platform": "EcoCash",
    "is_new_recip": true,
    "foreign_ip": false
  }'
```

Response:
```json
{
  "transaction": { ... },
  "fraud_score": 72,
  "risk_level": "high",
  "status": "flagged",
  "signals": {
    "unusual_amount": 40,
    "off_hours": 5,
    "new_recipient": 75,
    "rapid_transactions": 15,
    "location_mismatch": 5
  },
  "message": "Transaction flagged."
}
```

---

## Next step: Connect to your ML model (Step 4)

Open `utils/fraud_engine.py` and replace the `score_transaction()` function
body with a call to your trained scikit-learn or XGBoost model:

```python
import joblib
model = joblib.load("model.pkl")

def score_transaction(tx_data):
    features = [[tx_data["amount"], tx_data["hour"], ...]]
    score = int(model.predict_proba(features)[0][1] * 100)
    ...
```

Everything else stays the same.
