from flask import Flask
from flask_cors import CORS
from database import db
from routes.transactions import transactions_bp
from routes.alerts import alerts_bp
from routes.auth import auth_bp
from routes.admin import admin_bp

def create_app():
    app = Flask(__name__)
    CORS(app)  # Allow frontend to call this backend

    # --- Config ---
    app.config["SECRET_KEY"] = "ecoshield-secret-change-in-production"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///ecoshield.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # --- Init database ---
    db.init_app(app)

    # --- Register routes ---
    app.register_blueprint(auth_bp,         url_prefix="/api/auth")
    app.register_blueprint(transactions_bp, url_prefix="/api/transactions")
    app.register_blueprint(alerts_bp,       url_prefix="/api/alerts")
    app.register_blueprint(admin_bp,        url_prefix="/api/admin")

    # --- Create tables on first run ---
    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
