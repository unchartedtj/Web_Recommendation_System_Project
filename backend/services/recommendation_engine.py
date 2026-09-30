"""Recommendation engine: TF-IDF weighted requirement vectors + cosine similarity.

How it works
------------
1. "Training" (update_model): every OPEN opportunity becomes a row in an
   opportunity x unit matrix. A cell holds the importance of that unit to the
   opportunity (essential = 2, desirable = 1, not required = 0).
2. IDF weights are learnt from the binary version of that matrix with sklearn's
   TfidfTransformer(smooth_idf=True): idf(u) = ln((1 + n) / (1 + df(u))) + 1.
   A unit required by many opportunities (e.g. Database Systems) is less
   distinctive, so it gets a lower weight than a unit only one opportunity needs.
3. Opportunity vector = importance weight x idf  (non-zero only on its own units).
   Student vector     = mark / 100 x idf        (for every vocabulary unit).
4. match_score = cosine similarity of the two vectors (0 to 1).
5. Ranking: students who meet every ESSENTIAL minimum mark come first, then by
   match_score, then by the student's average mark in that opportunity's units.

The maths is kept in pure functions (build_model, build_student_vector, score,
evaluate_requirements, rank, recommend) that take plain Python data, so they can be
unit tested and used by evaluation/evaluate_engine.py without a database.
The RecommendationEngine class wraps them with database access and model persistence.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.metrics.pairwise import cosine_similarity

log = logging.getLogger(__name__)

MODEL_TYPE = "TF-IDF + Cosine Similarity"
IMPORTANCE_WEIGHTS = {"essential": 2.0, "desirable": 1.0}


class IncompleteGradesError(Exception):
    """The student's grade profile can't be scored (TC04). Nothing is written."""

    def __init__(self, missing: list | None = None, invalid: list | None = None):
        self.missing = missing or []
        self.invalid = invalid or []
        super().__init__(
            f"Grade profile is incomplete: {len(self.missing)} missing, "
            f"{len(self.invalid)} invalid unit(s)"
        )


# =============================================================================
# Pure functions (no database)
# =============================================================================

def requirements_fingerprint(opportunities: list[dict]) -> str:
    """Hash of the requirement structure. If it changes, the fitted model is stale."""
    canonical = sorted(
        (o["id"], sorted((r["unit_id"], r["importance"],
                          None if r.get("min_mark") is None else float(r["min_mark"]))
                         for r in o["requirements"]))
        for o in opportunities
    )
    return hashlib.sha256(json.dumps(canonical).encode()).hexdigest()


def build_model(opportunities: list[dict]) -> dict:
    """Fit the model ("training").

    opportunities: [{"id": int, "title": str, "requirements":
                     [{"unit_id": int, "importance": "essential"|"desirable",
                       "min_mark": float | None}, ...]}, ...]
    Returns a plain dict that can be saved with joblib.
    """
    opps = sorted(opportunities, key=lambda o: o["id"])
    vocabulary = sorted({r["unit_id"] for o in opps for r in o["requirements"]})
    model = {
        "model_type": MODEL_TYPE,
        "vocabulary": vocabulary,
        "idf": np.zeros(len(vocabulary)),
        "opportunity_ids": [o["id"] for o in opps],
        "opportunities": opps,
        "opp_vectors": np.zeros((len(opps), len(vocabulary))),
        "transformer": None,
        "fingerprint": requirements_fingerprint(opps),
        "fitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if not opps or not vocabulary:
        return model  # nothing open to recommend; sklearn can't fit an empty matrix

    col = {unit_id: j for j, unit_id in enumerate(vocabulary)}
    weights = np.zeros((len(opps), len(vocabulary)))
    for i, opp in enumerate(opps):
        for req in opp["requirements"]:
            weights[i, col[req["unit_id"]]] = IMPORTANCE_WEIGHTS[req["importance"]]

    # IDF is learnt from whether a unit is required at all (binary), not from its
    # importance, so "how many opportunities need this unit" is all that affects rarity.
    binary = (weights > 0).astype(float)
    transformer = TfidfTransformer(smooth_idf=True, norm=None).fit(binary)

    model["idf"] = transformer.idf_.copy()
    model["opp_vectors"] = weights * transformer.idf_
    model["transformer"] = transformer
    return model


def build_student_vector(marks: dict[int, float], model: dict) -> np.ndarray:
    """mark / 100 x idf for every vocabulary unit.

    Raises IncompleteGradesError if a vocabulary unit has no mark or an out-of-range mark.
    """
    missing = [u for u in model["vocabulary"] if u not in marks]
    invalid = [u for u in model["vocabulary"]
               if u in marks and not 0 <= float(marks[u]) <= 100]
    if missing or invalid:
        raise IncompleteGradesError(missing, invalid)
    raw = np.array([float(marks[u]) / 100.0 for u in model["vocabulary"]])
    return raw * model["idf"]


def score(student_vector: np.ndarray, model: dict) -> np.ndarray:
    """Cosine similarity between the student and every opportunity (0 to 1)."""
    if len(model["opportunity_ids"]) == 0:
        return np.array([])
    sims = cosine_similarity(student_vector.reshape(1, -1), model["opp_vectors"])[0]
    # All values are non-negative, so cosine is already within [0, 1]; clip float noise.
    return np.clip(sims, 0.0, 1.0)


def evaluate_requirements(marks: dict[int, float], requirements: list[dict],
                          unit_labels: dict[int, str] | None = None):
    """Check minimum marks for one opportunity.

    Returns (meets_requirements, unmet, avg_requirement_mark), where:
    - unmet lists EVERY requirement whose min_mark the student is below (essential or desirable),
    - meets_requirements is False only if an ESSENTIAL requirement is unmet,
    - avg_requirement_mark is the student's mean mark over the opportunity's units.
    """
    unit_labels = unit_labels or {}
    unmet = []
    for req in requirements:
        mark = float(marks[req["unit_id"]])
        if req.get("min_mark") is not None and mark < float(req["min_mark"]):
            unmet.append({
                "unit_id": req["unit_id"],
                "unit": unit_labels.get(req["unit_id"], str(req["unit_id"])),
                "importance": req["importance"],
                "required": float(req["min_mark"]),
                "your_mark": mark,
            })
    meets = not any(u["importance"] == "essential" for u in unmet)
    avg = float(np.mean([float(marks[r["unit_id"]]) for r in requirements])) if requirements else 0.0
    return meets, unmet, avg


def rank(results: list[dict]) -> list[dict]:
    """Order results and assign ranks 1..N.

    Order: eligible (meets_requirements) first, then match_score descending,
    then avg_requirement_mark descending (tie-breaker), then opportunity_id for stability.
    Scores are compared at 4 decimal places (as stored), so float noise can't break a real tie.
    """
    ordered = sorted(results, key=lambda r: (
        not r["meets_requirements"],
        -round(r["match_score"], 4),
        -r["avg_requirement_mark"],
        r["opportunity_id"],
    ))
    return [{**r, "rank": i} for i, r in enumerate(ordered, start=1)]


def recommend(marks: dict[int, float], model: dict,
              unit_labels: dict[int, str] | None = None) -> list[dict]:
    """Score and rank every opportunity in the model for one student."""
    if not model["opportunity_ids"]:
        return []
    scores = score(build_student_vector(marks, model), model)
    results = []
    for opp, s in zip(model["opportunities"], scores):
        meets, unmet, avg = evaluate_requirements(marks, opp["requirements"], unit_labels)
        results.append({
            "opportunity_id": opp["id"],
            "title": opp.get("title"),
            "match_score": round(float(s), 4),
            "match_percent": round(float(s) * 100, 2),
            "avg_requirement_mark": round(avg, 2),
            "meets_requirements": meets,
            "unmet_requirements": unmet,
        })
    return rank(results)


# =============================================================================
# RecommendationEngine (UML class): database access + persistence
# =============================================================================

class RecommendationEngine:
    """Matches the UML class:
        attributes: modelType, tfidfVectorizer, cosineSimilarity
        methods:    generateRecommendations(studentId), rankOpportunities(), updateModel()
    """

    def __init__(self, model_path: str | None = None):
        self.model_type = MODEL_TYPE
        self.tfidf_vectorizer: TfidfTransformer | None = None  # fitted in update_model()
        self.cosine_similarity = cosine_similarity
        self.model_path = model_path
        self.model: dict | None = None

    # ---- setup / persistence ----------------------------------------------------

    def init_app(self, app):
        self.model_path = app.config["ML_MODEL_PATH"]
        app.extensions["recommendation_engine"] = self
        # Load only from disk here, with no DB queries, so `flask db upgrade` works
        # on an empty database. A missing or stale model is refitted on first use.
        self.load()

    def load(self) -> bool:
        if not self.model_path or not os.path.exists(self.model_path):
            return False
        try:
            self._set_model(joblib.load(self.model_path))
            return True
        except Exception:  # corrupt or incompatible file: refit later
            log.warning("Could not load %s; it will be refitted", self.model_path, exc_info=True)
            self.model = None
            return False

    def _save(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        # Write to a temp file then atomically replace, so a crash never leaves half a model.
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.model_path), suffix=".tmp")
        os.close(fd)
        try:
            joblib.dump(self.model, tmp)
            os.replace(tmp, self.model_path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def _set_model(self, model: dict):
        self.model = model
        self.tfidf_vectorizer = model.get("transformer")

    # ---- database helpers ---------------------------------------------------------

    @staticmethod
    def _load_open_opportunities() -> list[dict]:
        """Open opportunities as plain dicts (the input format of build_model).

        Requirements on INACTIVE units are ignored: students can't submit grades
        for them, so they can't be scored.
        """
        from sqlalchemy.orm import selectinload

        from app.models import InternshipOpportunity, OpportunityPrecursor, OpportunityStatus

        rows = (InternshipOpportunity.query
                .filter_by(status=OpportunityStatus.OPEN)
                .options(selectinload(InternshipOpportunity.precursors)
                         .selectinload(OpportunityPrecursor.unit),
                         selectinload(InternshipOpportunity.partner))
                .order_by(InternshipOpportunity.opportunity_id)
                .all())
        return [{
            "id": o.opportunity_id,
            "title": o.title,
            "sector": o.sector,
            "organization": o.partner.organization_name if o.partner else None,
            "requirements": [{
                "unit_id": p.unit_id,
                "importance": p.importance,
                "min_mark": None if p.min_mark is None else float(p.min_mark),
            } for p in o.precursors if p.unit.is_active],
        } for o in rows]

    # ---- UML: updateModel() ---------------------------------------------------------

    def update_model(self, opportunities: list[dict] | None = None) -> dict:
        """Refit on all OPEN opportunities and save to disk ("training")."""
        data = opportunities if opportunities is not None else self._load_open_opportunities()
        self._set_model(build_model(data))
        self._save()
        log.info("Recommendation model fitted: %d opportunities, %d units",
                 len(self.model["opportunity_ids"]), len(self.model["vocabulary"]))
        return self.model

    def ensure_fresh(self) -> list[dict]:
        """Refit if the model is missing or no longer matches the database."""
        data = self._load_open_opportunities()
        if self.model is None or self.model.get("fingerprint") != requirements_fingerprint(data):
            self.update_model(data)
        return data

    # ---- validation (TC04) ----------------------------------------------------------

    def validate_profile(self, student_id: int) -> dict[int, float]:
        """Return the latest grade profile as {unit_id: mark}.

        It must hold every ACTIVE catalog unit (all 12) with a mark from 0 to 100.
        Otherwise IncompleteGradesError is raised. The model vocabulary only ever
        contains active units, so this also covers everything scoring needs.
        """
        from app.models import AcademicUnit, GradeProfile

        profile = (GradeProfile.query.filter_by(student_id=student_id)
                   .order_by(GradeProfile.submission_date.desc(),
                             GradeProfile.profile_id.desc())
                   .first())
        marks = {g.unit_id: float(g.grade_value) for g in profile.grades} if profile else {}

        active = (AcademicUnit.query.filter_by(is_active=True)
                  .order_by(AcademicUnit.unit_name).all())

        missing = [{"unit_id": u.unit_id, "unit_name": u.unit_name}
                   for u in active if u.unit_id not in marks]
        invalid = [{"unit_id": u.unit_id, "unit_name": u.unit_name, "mark": marks[u.unit_id]}
                   for u in active if u.unit_id in marks and not 0 <= marks[u.unit_id] <= 100]
        if missing or invalid:
            raise IncompleteGradesError(missing, invalid)
        return marks

    # ---- UML: rankOpportunities() ---------------------------------------------------

    def rank_opportunities(self, results: list[dict]) -> list[dict]:
        return rank(results)

    # ---- UML: generateRecommendations(studentId) ------------------------------------

    def generate_recommendations(self, student_id: int) -> list[dict]:
        """Validate, score and rank, then replace the student's saved recommendations
        in one transaction. Returns the ranked list."""
        from app.extensions import db
        from app.models import AcademicUnit, Recommendation

        opportunities = self.ensure_fresh()
        marks = self.validate_profile(student_id)  # raises before anything is written

        labels = {u.unit_id: u.unit_name
                  for u in AcademicUnit.query.filter(
                      AcademicUnit.unit_id.in_(self.model["vocabulary"]))}
        results = recommend(marks, self.model, labels)
        meta = {o["id"]: o for o in opportunities}
        for r in results:
            r["organization"] = meta[r["opportunity_id"]]["organization"]
            r["sector"] = meta[r["opportunity_id"]]["sector"]

        generated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        try:
            Recommendation.query.filter_by(student_id=student_id).delete()
            for r in results:
                db.session.add(Recommendation(
                    student_id=student_id,
                    opportunity_id=r["opportunity_id"],
                    match_score=r["match_score"],
                    rank=r["rank"],
                    meets_requirements=r["meets_requirements"],
                    avg_requirement_mark=r["avg_requirement_mark"],
                    unmet_requirements=r["unmet_requirements"],
                    generated_at=generated_at,
                ))
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        for r in results:
            r["generated_at"] = generated_at.isoformat(timespec="seconds") + "Z"
        return results


def get_engine() -> RecommendationEngine:
    """The app's shared engine instance (created in create_app)."""
    from flask import current_app
    return current_app.extensions["recommendation_engine"]
