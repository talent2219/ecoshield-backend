from database import db
from datetime import datetime


class User(db.Model):
    """A mobile money account holder."""
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    phone         = db.Column(db.String(20),  unique=True, nullable=False)
    platform      = db.Column(db.String(20),  nullable=False)   # EcoCash | OneMoney | Telecash
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin      = db.Column(db.Boolean, default=False)
    risk_score    = db.Column(db.Float,   default=0.0)
    is_frozen     = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    transactions  = db.relationship("Transaction", backref="user", lazy=True)
    alerts        = db.relationship("Alert",       backref="user", lazy=True)

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "phone":      self.phone,
            "platform":   self.platform,
            "risk_score": round(self.risk_score, 1),
            "is_frozen":  self.is_frozen,
            "created_at": self.created_at.isoformat(),
        }


class Transaction(db.Model):
    """Every transaction that passes through EcoShield."""
    __tablename__ = "transactions"

    id            = db.Column(db.Integer,     primary_key=True)
    tx_ref        = db.Column(db.String(20),  unique=True, nullable=False)   # e.g. TX-A9F21
    user_id       = db.Column(db.Integer,     db.ForeignKey("users.id"), nullable=False)
    tx_type       = db.Column(db.String(20),  nullable=False)   # send | receive | withdraw | payment
    amount        = db.Column(db.Float,       nullable=False)
    recipient     = db.Column(db.String(100), nullable=True)    # phone or merchant name
    platform      = db.Column(db.String(20),  nullable=False)
    hour          = db.Column(db.Integer,     nullable=False)   # 0-23
    is_new_recip  = db.Column(db.Boolean,     default=False)
    is_rapid_fire = db.Column(db.Boolean,     default=False)
    foreign_ip    = db.Column(db.Boolean,     default=False)
    fraud_score   = db.Column(db.Float,       default=0.0)
    risk_level    = db.Column(db.String(10),  default="low")    # low | medium | high
    status        = db.Column(db.String(20),  default="clear")  # clear | flagged | blocked
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":           self.id,
            "tx_ref":       self.tx_ref,
            "user_id":      self.user_id,
            "user_name":    self.user.name if self.user else "Unknown",
            "tx_type":      self.tx_type,
            "amount":       self.amount,
            "recipient":    self.recipient,
            "platform":     self.platform,
            "fraud_score":  round(self.fraud_score, 1),
            "risk_level":   self.risk_level,
            "status":       self.status,
            "created_at":   self.created_at.isoformat(),
        }


class Alert(db.Model):
    """Fraud alert sent to a user or admin."""
    __tablename__ = "alerts"

    id             = db.Column(db.Integer,  primary_key=True)
    user_id        = db.Column(db.Integer,  db.ForeignKey("users.id"), nullable=False)
    transaction_id = db.Column(db.Integer,  db.ForeignKey("transactions.id"), nullable=True)
    alert_type     = db.Column(db.String(30), nullable=False)  # fraud | login | withdrawal | sim_swap
    severity       = db.Column(db.String(10), nullable=False)  # low | medium | high
    title          = db.Column(db.String(200), nullable=False)
    message        = db.Column(db.Text,       nullable=False)
    is_read        = db.Column(db.Boolean,    default=False)
    action_taken   = db.Column(db.String(30), nullable=True)   # confirmed | dismissed | blocked
    created_at     = db.Column(db.DateTime,   default=datetime.utcnow)

    transaction    = db.relationship("Transaction", backref="alerts", lazy=True)

    def to_dict(self):
        return {
            "id":             self.id,
            "user_id":        self.user_id,
            "transaction_id": self.transaction_id,
            "alert_type":     self.alert_type,
            "severity":       self.severity,
            "title":          self.title,
            "message":        self.message,
            "is_read":        self.is_read,
            "action_taken":   self.action_taken,
            "created_at":     self.created_at.isoformat(),
        }
