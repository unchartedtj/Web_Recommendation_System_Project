"""Flask application factory.

An "application factory" is a function that BUILDS and returns the app, instead of
creating it once at import time. That lets us build it with different settings:
DevelopmentConfig for `flask run`, TestingConfig for pytest.

Request flow, for orientation:
    Browser/React → HTTP request → Flask → the matching route function (a "blueprint")
    → validators / services / models → database → JSON response back to React.
"""
from flask import Flask, jsonify

from app.config import DevelopmentConfig
from app.extensions import cors, db, jwt, migrate, recommendation_engine


def create_app(config_class=DevelopmentConfig) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)   # load settings (database URI, JWT secret, ...)

    # Fail fast at startup if the match weights are wrong (e.g. they don't add up to 1).
    from services.recommendation_engine import validate_weights
    app.config["MATCH_WEIGHTS"] = validate_weights(app.config["MATCH_WEIGHTS"])

    # Connect each extension to this app.
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    # Only the Vite dev server (or FRONTEND_ORIGIN) may call the API from a browser.
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGIN"]}})
    recommendation_engine.init_app(app)  # loads ml_models/engine.joblib if present

    # Imported here (not at the top of the file) to avoid circular imports: these
    # modules themselves import from `app`.
    from app import models  # noqa: F401  (register models with SQLAlchemy/Alembic)
    from app.auth import auth_bp
    from app.cli import register_cli
    from app.errors import register_error_handlers
    from app.opportunities import opportunities_bp
    from app.recommendations import recommendations_bp
    from app.students import students_bp
    from app.admin import admin_bp
    from app.applications import applications_bp

    # A "blueprint" is a group of related routes. Registering it switches those routes on.
    app.register_blueprint(auth_bp)               # /api/auth/...
    app.register_blueprint(opportunities_bp)      # /api/units, /skills, /sectors, /opportunities, /partner/...
    app.register_blueprint(recommendations_bp)    # /api/recommendations, /api/admin/model/retrain
    app.register_blueprint(students_bp)           # /api/student/profile
    app.register_blueprint(admin_bp)              # /api/admin/skills, /api/admin/sectors
    app.register_blueprint(applications_bp)       # /api/applications, /api/partner/.../candidates
    register_error_handlers(app)                  # turn every error into {"error", "fields"} JSON
    register_cli(app)                             # `flask create-admin`, `flask seed-data`

    # A tiny endpoint to check the server is up: GET /api/health → {"status": "ok"}
    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    return app
