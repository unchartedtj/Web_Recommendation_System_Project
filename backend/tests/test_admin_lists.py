"""Tests for the admin API that manages the preset skills and sectors lists."""
import pytest

from app.models import Sector, Skill
from app.seed.catalog import DEFAULT_ADMIN
from tests.conftest import auth_header, login, register_and_login


@pytest.fixture
def admin_token(client, seeded):
    # `seeded` creates the default admin (username "Admin").
    return login(client, DEFAULT_ADMIN["name"], DEFAULT_ADMIN["password"])


# ---- Skills ----------------------------------------------------------------------------------

def test_admin_creates_a_skill(client, admin_token):
    res = client.post("/api/admin/skills", json={"name": "Docker", "category": "Tools"},
                      headers=auth_header(admin_token))
    assert res.status_code == 201
    assert res.get_json()["skill"]["is_active"] is True
    # It immediately appears in the public list.
    groups = client.get("/api/skills", headers=auth_header(admin_token)).get_json()["categories"]
    assert "Docker" in [s["name"] for g in groups for s in g["skills"]]


def test_duplicate_skill_name_returns_409(client, admin_token):
    res = client.post("/api/admin/skills", json={"name": "python", "category": "Programming"},
                      headers=auth_header(admin_token))
    assert res.status_code == 409


def test_missing_fields_return_400(client, admin_token):
    res = client.post("/api/admin/skills", json={"name": ""}, headers=auth_header(admin_token))
    assert res.status_code == 400
    assert {"name", "category"} <= set(res.get_json()["fields"])


def test_unused_skill_is_deleted(client, admin_token):
    php = Skill.query.filter_by(name="PHP").one()           # no opportunity requires PHP
    res = client.delete(f"/api/admin/skills/{php.skill_id}", headers=auth_header(admin_token))
    assert res.get_json()["result"] == "deleted"
    assert Skill.query.filter_by(name="PHP").first() is None


def test_skill_in_use_is_deactivated_and_leaves_the_model(client, admin_token, engine):
    sql = Skill.query.filter_by(name="SQL").one()           # required by 3 opportunities
    assert sql.skill_id in engine.model["skill_vocabulary"]

    res = client.delete(f"/api/admin/skills/{sql.skill_id}", headers=auth_header(admin_token))

    assert res.get_json()["result"] == "deactivated"
    assert Skill.query.filter_by(name="SQL").one().is_active is False
    assert sql.skill_id not in engine.model["skill_vocabulary"]      # model was refitted
    groups = client.get("/api/skills", headers=auth_header(admin_token)).get_json()["categories"]
    assert "SQL" not in [s["name"] for g in groups for s in g["skills"]]


def test_admin_can_rename_and_reactivate_a_skill(client, admin_token):
    sql = Skill.query.filter_by(name="SQL").one()
    client.delete(f"/api/admin/skills/{sql.skill_id}", headers=auth_header(admin_token))
    res = client.put(f"/api/admin/skills/{sql.skill_id}",
                     json={"name": "SQL (MySQL / PostgreSQL)", "is_active": True},
                     headers=auth_header(admin_token))
    assert res.status_code == 200
    assert res.get_json()["skill"] == {"skill_id": sql.skill_id, "name": "SQL (MySQL / PostgreSQL)",
                                       "category": "Data", "is_active": True}


# ---- Sectors ---------------------------------------------------------------------------------

def test_admin_creates_and_deletes_an_unused_sector(client, admin_token):
    created = client.post("/api/admin/sectors", json={"name": "Fintech"},
                          headers=auth_header(admin_token)).get_json()["sector"]
    res = client.delete(f"/api/admin/sectors/{created['sector_id']}",
                        headers=auth_header(admin_token))
    assert res.get_json()["result"] == "deleted"


def test_sector_in_use_is_deactivated(client, admin_token):
    data = Sector.query.filter_by(name="Data Analytics & AI").one()   # used by an opportunity
    res = client.delete(f"/api/admin/sectors/{data.sector_id}", headers=auth_header(admin_token))
    assert res.get_json()["result"] == "deactivated"
    names = [s["name"] for s in
             client.get("/api/sectors", headers=auth_header(admin_token)).get_json()["sectors"]]
    assert "Data Analytics & AI" not in names


# ---- Access ----------------------------------------------------------------------------------

def test_non_admins_get_403(client, seeded, student_payload):
    token = register_and_login(client, student_payload)
    assert client.get("/api/admin/skills", headers=auth_header(token)).status_code == 403
    assert client.post("/api/admin/sectors", json={"name": "X"},
                       headers=auth_header(token)).status_code == 403
