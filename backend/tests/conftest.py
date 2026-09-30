"""Pytest fixtures.

Tests run against a separate MySQL database (TEST_DB_NAME, default wbl_placement_test),
which is created automatically if missing. Tables are rebuilt for every test, so each
test starts from an empty schema.
"""
import os

import pymysql
import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db


def _ensure_test_database():
    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{TestingConfig.TEST_DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        conn.close()


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    _ensure_test_database()
    app = create_app(TestingConfig)
    # Keep the test model file away from the real backend/ml_models/engine.joblib.
    model_path = str(tmp_path_factory.mktemp("ml_models") / "engine.joblib")
    app.config["ML_MODEL_PATH"] = model_path
    app.extensions["recommendation_engine"].model_path = model_path
    return app


@pytest.fixture(autouse=True)
def _fresh_schema(app):
    engine = app.extensions["recommendation_engine"]
    with app.app_context():
        db.drop_all()
        db.create_all()
        engine.model = None  # the DB is empty again, so forget the previous test's model
        yield
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def engine(app):
    return app.extensions["recommendation_engine"]


@pytest.fixture
def seeded(app):
    """Seed the catalogue (12 units, 2 demo partners, 5 opportunities).
    Returns {unit_name: unit_id}."""
    from app.models import AcademicUnit
    from app.seed.seeder import seed_all
    seed_all()
    return {u.unit_name: u.unit_id for u in AcademicUnit.query.all()}


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client, payload: dict) -> str:
    """Register via the API and return an access token."""
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201, res.get_json()
    res = client.post("/api/auth/login",
                      json={"email": payload["email"], "password": payload["password"]})
    return res.get_json()["access_token"]


def login(client, email: str, password: str) -> str:
    return client.post("/api/auth/login",
                       json={"email": email, "password": password}).get_json()["access_token"]


@pytest.fixture
def student_payload():
    """Valid student registration body (the data used for test case TC01)."""
    return {
        "role": "student",
        "email": "jane.doe@strathmore.edu",
        "password": "Passw0rd123",
        "confirm_password": "Passw0rd123",
        "admission_no": "168003",
        "first_name": "Jane",
        "last_name": "Doe",
        "course": "BSc Informatics and Computer Science",
        "year_of_study": 3,
    }


@pytest.fixture
def partner_payload():
    return {
        "role": "industry_partner",
        "email": "hr@acme.co.ke",
        "password": "Partner2024",
        "confirm_password": "Partner2024",
        "organization_name": "Acme Kenya Ltd",
        "contact_person": "John Kamau",
        "phone": "+254 712 345678",
    }
