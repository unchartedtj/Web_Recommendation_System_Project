"""Extension instances, created unbound and initialised inside create_app()."""
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from services.recommendation_engine import RecommendationEngine

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
recommendation_engine = RecommendationEngine()
