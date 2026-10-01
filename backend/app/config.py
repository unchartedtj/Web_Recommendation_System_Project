"""Application configuration, loaded from environment variables (.env).

Settings live in backend/.env (not in code), so each machine or server can use its own
database password, secret key and so on without editing Python files.
os.getenv("NAME", "default") reads a setting and falls back to the default if it's missing.
"""
import os
from datetime import timedelta
from urllib.parse import quote_plus

from dotenv import load_dotenv

# Load backend/.env so both `flask run` and pytest see the same settings.
# __file__ is this file (backend/app/config.py); two dirname() calls go up to backend/.
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))


def build_db_uri(db_name: str) -> str:
    """Build a PyMySQL SQLAlchemy URI for the given database name.

    The result looks like: mysql+pymysql://root:@localhost:3306/wbl_placement?charset=utf8mb4
      mysql+pymysql  → database type + the Python driver used to talk to it
      root:          → username:password
      localhost:3306 → where the MySQL server is running
      charset        → utf8mb4 supports every character (including emoji)
    """
    user = os.getenv("DB_USER", "root")
    password = quote_plus(os.getenv("DB_PASSWORD", ""))  # escape special characters like @ or /
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}?charset=utf8mb4"


class Config:
    """Base settings shared by every environment."""

    # Which database SQLAlchemy connects to.
    SQLALCHEMY_DATABASE_URI = build_db_uri(os.getenv("DB_NAME", "wbl_placement"))
    # Turns off an old, memory-hungry change-tracking feature we don't need.
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Recycle connections so MySQL's wait_timeout doesn't hand us dead ones.
    # pool_pre_ping checks a connection still works before using it.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # Secret used to SIGN login tokens (JWTs). Anyone who knows it could forge a token,
    # so in real use it must be a long random value set in .env.
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-insecure-secret-change-me")
    # How long a login lasts before the user must log in again (default 60 minutes).
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "60"))
    )

    # The website address allowed to call this API from a browser (CORS).
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

    # Where the fitted recommendation model is saved (backend/ml_models/engine.joblib).
    ML_MODEL_PATH = os.getenv(
        "ML_MODEL_PATH",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml_models", "engine.joblib"),
    )


class DevelopmentConfig(Config):
    """Used by `flask run` on your laptop. DEBUG shows detailed errors and auto-reloads."""
    DEBUG = True


class TestingConfig(Config):
    """Points at a separate database so tests never touch real data."""
    TESTING = True
    TEST_DB_NAME = os.getenv("TEST_DB_NAME", "wbl_placement_test")
    SQLALCHEMY_DATABASE_URI = build_db_uri(TEST_DB_NAME)
    # A fixed key so tests don't depend on what's in your .env.
    JWT_SECRET_KEY = "test-secret-key-that-is-long-enough-for-hs256"
