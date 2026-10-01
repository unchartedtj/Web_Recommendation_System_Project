"""Extension instances, created unbound and initialised inside create_app().

Why create them here and not inside create_app()? Other files (models, routes) need
to import `db` etc. If they imported them from app/__init__.py we'd get circular
imports. So they're created "empty" here, and create_app() connects them to the app
with .init_app(app).
"""
from flask_cors import CORS                  # lets the React site (another port) call the API
from flask_jwt_extended import JWTManager    # login tokens (JWT)
from flask_migrate import Migrate            # `flask db migrate/upgrade` schema changes
from flask_sqlalchemy import SQLAlchemy      # the ORM: Python classes ↔ database tables

from services.recommendation_engine import RecommendationEngine

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
recommendation_engine = RecommendationEngine()   # one shared engine for the whole app
