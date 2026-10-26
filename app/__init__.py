from flask import Flask, render_template
from .config import Config
from .extensions import db, migrate, login_manager


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from . import models
    from .data_collection import bp as data_bp
    from .analytics import bp as analytics_bp
    from .user_access import bp as access_bp
    from .ai_assistant import bp as ai_bp
    for blueprint in (data_bp, analytics_bp, access_bp, ai_bp):
        app.register_blueprint(blueprint)

    @app.get("/")
    def home():
        return render_template("home.html")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
