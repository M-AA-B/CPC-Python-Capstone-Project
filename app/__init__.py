import os
from flask import Flask, render_template
from app.extensions import db


def create_app(test_config=None):
    """Application factory pattern for the Carbon Tracker app."""
    app = Flask(__name__)
    
    # Explicitly set secret key for flash messages and sessions
    app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-super-secure-12345')
    app.config['SECRET_KEY'] = app.secret_key
    
    # 1. Set default configurations first
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL', 
        'postgresql+psycopg://carbon_user:password@db:5432/carbon_tracker'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 2. Override with test_config BEFORE initializing extensions if provided
    if test_config:
        app.config.update(test_config)

    # 3. Initialize Flask extensions with the finalized configuration
    db.init_app(app)

    # Register Blueprints
    from app.data_collection import bp as data_bp
    from app.analytics import bp as analytics_bp
    from app.user_access import bp as access_bp
    from app.ai_assistant import bp as ai_bp
    for blueprint in (data_bp, analytics_bp, access_bp, ai_bp):
        app.register_blueprint(blueprint)

    @app.get("/")
    def home():
        return render_template("home.html")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app

    return app