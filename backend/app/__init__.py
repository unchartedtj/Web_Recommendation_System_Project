"""Flask application factory."""
from flask import Flask, jsonify

from app.config import DevelopmentConfig
from app.extensions import cors, db, jwt, migrate, recommendation_engine


def create_app(config_class=DevelopmentConfig) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    # Only the Vite dev server (or FRONTEND_ORIGIN) may call the API from a browser.
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGIN"]}})
    recommendation_engine.init_app(app)  # loads ml_models/engine.joblib if present

    from app import models  # noqa: F401  (register models with SQLAlchemy/Alembic)
    from app.auth import auth_bp
    from app.cli import register_cli
    from app.errors import register_error_handlers
    from app.opportunities import opportunities_bp
    from app.recommendations import recommendations_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(opportunities_bp)
    app.register_blueprint(recommendations_bp)
    register_error_handlers(app)
    register_cli(app)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    return app
