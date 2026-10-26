"""The admin Model page and SUS results (test case TC10).

    GET /api/admin/model            what the model learnt + the offline evaluation results
    GET /api/admin/sus              usability questionnaire summary
    GET /api/admin/sus/export.csv   every response as a CSV file
(Retraining is POST /api/admin/model/retrain, in app/recommendations/routes.py.)
"""
import csv
import os

from flask import current_app, jsonify

from app.admin import admin_bp
from app.admin.common import ADMIN, csv_response, iso
from app.auth.decorators import role_required
from app.models import AcademicUnit, Skill, SusResponse
from app.sus.services import summary
from services.recommendation_engine import DEFAULT_WEIGHTS, get_engine

# Columns of evaluation/results.csv worth showing (it also has every mark, which isn't).
RESULT_COLUMNS = ["student", "group", "expected", "grades_only_rank1", "grades_only_top1_hit",
                  "grades_skills_rank1", "grades_skills_top1_hit", "all_three_rank1",
                  "all_three_top1_hit", "all_three_top3_hit"]


def _read_csv(name: str, columns: list[str] | None = None) -> list[dict] | None:
    path = os.path.join(current_app.root_path, os.pardir, "evaluation", name)
    if not os.path.exists(path):
        return None
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if columns:
        rows = [{c: r.get(c) for c in columns} for r in rows]
    return rows


@admin_bp.get("/model")
@role_required(ADMIN)
def model_info():
    engine = get_engine()
    engine.ensure_fresh()                       # refit first if it's out of date
    m = engine.model or {}
    units = {u.unit_id: u.unit_name for u in AcademicUnit.query.all()}
    skills = {s.skill_id: s.name for s in Skill.query.all()}
    return jsonify({
        "fitted_at": m.get("fitted_at"),
        "model_type": m.get("model_type"),
        "n_opportunities": len(m.get("opportunity_ids", [])),
        "unit_idf": [{"unit_id": uid, "name": units.get(uid), "idf": round(float(w), 4)}
                     for uid, w in zip(m.get("vocabulary", []), m.get("idf", []))],
        "skill_idf": [{"skill_id": sid, "name": skills.get(sid), "idf": round(float(w), 4)}
                      for sid, w in zip(m.get("skill_vocabulary", []), m.get("skill_idf", []))],
        "match_weights": current_app.config.get("MATCH_WEIGHTS", DEFAULT_WEIGHTS),
        "evaluation": {"ablation": _read_csv("ablation.csv"),
                       "results": _read_csv("results.csv", RESULT_COLUMNS)},
    })


@admin_bp.get("/sus")
@role_required(ADMIN)
def sus_results():
    return jsonify(summary())


@admin_bp.get("/sus/export.csv")
@role_required(ADMIN)
def sus_export():
    header = ["response_id", "role", *[f"q{i}" for i in range(1, 11)], "sus_score", "comments",
              "created_at", "updated_at"]
    rows = [[r.response_id, r.role, *r.answers, r.sus_score, r.comments or "",
             iso(r.created_at), iso(r.updated_at)]
            for r in SusResponse.query.order_by(SusResponse.response_id)]
    return csv_response("sus_responses.csv", header, rows)
