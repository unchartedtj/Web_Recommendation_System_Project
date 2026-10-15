from __future__ import annotations

import hashlib      # SHA-256 hashing, used for the "is the model stale?" fingerprint
import json         # turn Python data into text so it can be hashed
import logging      # write info/warning messages to the server log
import os           # file paths and file operations
import tempfile     # create a temporary file when saving the model safely
from datetime import datetime, timezone

import joblib       # saves/loads Python objects (incl. numpy arrays) to/from disk
import numpy as np  # fast maths on arrays (vectors and matrices)
from sklearn.feature_extraction.text import TfidfTransformer   # computes the IDF weights
from sklearn.metrics.pairwise import cosine_similarity         # computes the match scores

log = logging.getLogger(__name__)

# Name shown in the admin retrain response and stored with the model.
MODEL_TYPE = "TF-IDF + Cosine Similarity (grades, skills) + interest match"
# Importance level counts in an opportunity's vector.
# Essential counts double, so it pulls the score more than desirable does.
IMPORTANCE_WEIGHTS = {"essential": 2.0, "desirable": 1.0}
# Default weights of the three parts (the app uses config MATCH_WEIGHTS, which has the same values).
DEFAULT_WEIGHTS = {"grades": 0.60, "skills": 0.25, "interests": 0.15}
WEIGHT_KEYS = ("grades", "skills", "interests")


class IncompleteGradesError(Exception):

    def __init__(self, missing: list | None = None, invalid: list | None = None):
        self.missing = missing or []   # `or []` turns None into an empty list
        self.invalid = invalid or []
        super().__init__(
            f"Grade profile is incomplete: {len(self.missing)} missing, "
            f"{len(self.invalid)} invalid unit(s)"
        )



# Pure functions (no database)

def validate_weights(weights: dict) -> dict:
    if set(weights) != set(WEIGHT_KEYS):
        raise ValueError(f"MATCH_WEIGHTS must have exactly the keys {WEIGHT_KEYS}")
    clean = {k: float(weights[k]) for k in WEIGHT_KEYS}
    if any(v < 0 for v in clean.values()):
        raise ValueError("MATCH_WEIGHTS values can't be negative")
    if abs(sum(clean.values()) - 1.0) > 1e-9:
        raise ValueError(f"MATCH_WEIGHTS must add up to 1 (got {sum(clean.values())})")
    return clean


def requirements_fingerprint(opportunities: list[dict]) -> str:
    canonical = sorted(
        (o["id"],
         sorted((r["unit_id"], r["importance"],
                 None if r.get("min_mark") is None else float(r["min_mark"]))
                for r in o["requirements"]),
         sorted((s["skill_id"], s["importance"]) for s in o.get("skills", [])),
         o.get("sector_id"))
        for o in opportunities
    )
    return hashlib.sha256(json.dumps(canonical).encode()).hexdigest()


def _fit_weighted_tfidf(opps: list[dict], items_key: str, id_key: str):
    # The vocabulary = every item required by at least one opportunity (sorted ids = columns).
    vocabulary = sorted({it[id_key] for o in opps for it in o.get(items_key, [])})
    if not opps or not vocabulary:
        # Nothing to learn from (sklearn can't fit an empty matrix).
        return vocabulary, np.zeros(len(vocabulary)), np.zeros((len(opps), len(vocabulary))), None

    col = {item_id: j for j, item_id in enumerate(vocabulary)}   # item id → column number
    # weights[row, column] = 2 (essential) or 1 (desirable); 0 if not required.
    weights = np.zeros((len(opps), len(vocabulary)))
    for i, opp in enumerate(opps):
        for it in opp.get(items_key, []):
            weights[i, col[it[id_key]]] = IMPORTANCE_WEIGHTS[it["importance"]]

    # IDF is learnt from whether an item is required at all (binary), not from its
    # importance, so "how many opportunities need this item" is all that affects rarity.
    binary = (weights > 0).astype(float)
    # norm=None: don't rescale rows; smooth_idf=True: the "+1" smoothing in the formula.
    transformer = TfidfTransformer(smooth_idf=True, norm=None).fit(binary)
    # numpy multiplies each column by that item's IDF weight ("broadcasting").
    return vocabulary, transformer.idf_.copy(), weights * transformer.idf_, transformer


def build_model(opportunities: list[dict]) -> dict:
    # Sort by id so row i of every matrix always means the same opportunity.
    opps = sorted(opportunities, key=lambda o: o["id"])
    vocab, idf, vectors, transformer = _fit_weighted_tfidf(opps, "requirements", "unit_id")
    s_vocab, s_idf, s_vectors, s_transformer = _fit_weighted_tfidf(opps, "skills", "skill_id")
    return {
        "model_type": MODEL_TYPE,
        "opportunity_ids": [o["id"] for o in opps],            # row i = opportunity_ids[i]
        "opportunities": opps,                                 # kept for titles/requirements
        "sector_ids": [o.get("sector_id") for o in opps],      # for the interest score
        # --- units model (grade_score) ---
        "vocabulary": vocab,                                   # column j = unit vocabulary[j]
        "idf": idf,
        "opp_vectors": vectors,
        "transformer": transformer,
        # --- skills model (skill_score) ---
        "skill_vocabulary": s_vocab,                           # column j = skill s_vocab[j]
        "skill_idf": s_idf,
        "skill_vectors": s_vectors,
        "skill_transformer": s_transformer,
        "fingerprint": requirements_fingerprint(opps),         # used to detect staleness
        "fitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def build_student_vector(marks: dict[int, float], model: dict) -> np.ndarray:
    missing = [u for u in model["vocabulary"] if u not in marks]
    invalid = [u for u in model["vocabulary"]
               if u in marks and not 0 <= float(marks[u]) <= 100]
    if missing or invalid:
        raise IncompleteGradesError(missing, invalid)
    raw = np.array([float(marks[u]) / 100.0 for u in model["vocabulary"]])
    return raw * model["idf"]   # element-by-element multiply with the IDF weights


def build_skill_vector(skill_ids, model: dict) -> np.ndarray:
    chosen = set(skill_ids)
    raw = np.array([1.0 if s in chosen else 0.0 for s in model["skill_vocabulary"]])
    return raw * model["skill_idf"]


def _cosine(vector: np.ndarray, matrix: np.ndarray, n_rows: int) -> np.ndarray:
    if n_rows == 0:
        return np.array([])
    if matrix.shape[1] == 0 or not np.any(vector):
        return np.zeros(n_rows)
    # sklearn expects 2-D input, so reshape(1, -1) turns the vector into a 1-row matrix.
    sims = cosine_similarity(vector.reshape(1, -1), matrix)[0]
    # All values are non-negative, so cosine is already within [0, 1]; clip float noise.
    return np.clip(sims, 0.0, 1.0)


def score(student_vector: np.ndarray, model: dict) -> np.ndarray:
    return _cosine(student_vector, model["opp_vectors"], len(model["opportunity_ids"]))


def skill_scores(student_skill_vector: np.ndarray, model: dict) -> np.ndarray:
    return _cosine(student_skill_vector, model["skill_vectors"], len(model["opportunity_ids"]))


def interest_scores(sector_ids, model: dict) -> np.ndarray:
    chosen = set(sector_ids)
    return np.array([1.0 if s in chosen else 0.0 for s in model["sector_ids"]])


def combine(grade: float, skill: float, interest: float, weights: dict) -> float:
    return (weights["grades"] * grade + weights["skills"] * skill
            + weights["interests"] * interest)


def missing_skills(skill_ids, opp_skills: list[dict],
                   skill_labels: dict[int, str] | None = None) -> tuple[list, list]:
    labels = skill_labels or {}
    have = set(skill_ids)
    essential = [labels.get(s["skill_id"], str(s["skill_id"])) for s in opp_skills
                 if s["importance"] == "essential" and s["skill_id"] not in have]
    desirable = [labels.get(s["skill_id"], str(s["skill_id"])) for s in opp_skills
                 if s["importance"] == "desirable" and s["skill_id"] not in have]
    return essential, desirable


def evaluate_requirements(marks: dict[int, float], requirements: list[dict],
                          unit_labels: dict[int, str] | None = None):
    unit_labels = unit_labels or {}   # unit_id → name, for readable messages
    unmet = []
    for req in requirements:
        mark = float(marks[req["unit_id"]])
        # Only check units that HAVE a minimum mark.
        if req.get("min_mark") is not None and mark < float(req["min_mark"]):
            unmet.append({
                "unit_id": req["unit_id"],
                "unit": unit_labels.get(req["unit_id"], str(req["unit_id"])),
                "importance": req["importance"],
                "required": float(req["min_mark"]),
                "your_mark": mark,
            })
    # Eligible unless at least one ESSENTIAL minimum was missed.
    meets = not any(u["importance"] == "essential" for u in unmet)
    # Average mark over this opportunity's units (used as the ranking tie-breaker).
    avg = float(np.mean([float(marks[r["unit_id"]]) for r in requirements])) if requirements else 0.0
    return meets, unmet, avg


def rank(results: list[dict]) -> list[dict]:
    # Python sorts by the key tuple left to right, smallest first:
    #   not meets  → False (eligible) sorts before True (ineligible)
    #   -score     → negated so HIGHER scores come first
    #   -avg       → negated so HIGHER averages come first
    #   id         → final tie-breaker so the order is always the same
    ordered = sorted(results, key=lambda r: (
        not r["meets_requirements"],
        -round(r["match_score"], 4),
        -r["avg_requirement_mark"],
        r["opportunity_id"],
    ))
    # Copy each result and add its position: 1, 2, 3, ...
    return [{**r, "rank": i} for i, r in enumerate(ordered, start=1)]


def recommend(marks: dict[int, float], model: dict,
              unit_labels: dict[int, str] | None = None, *,
              skill_ids=(), sector_ids=(), weights: dict | None = None,
              skill_labels: dict[int, str] | None = None) -> list[dict]:
    if not model["opportunity_ids"]:
        return []   # no open opportunities → nothing to recommend
    weights = validate_weights(weights or DEFAULT_WEIGHTS)
    grades = score(build_student_vector(marks, model), model)
    skills = skill_scores(build_skill_vector(skill_ids, model), model)
    interests = interest_scores(sector_ids, model)

    results = []
    # zip pairs each opportunity with its three scores (same order as the matrix rows).
    for opp, g, s, i in zip(model["opportunities"], grades, skills, interests):
        meets, unmet, avg = evaluate_requirements(marks, opp["requirements"], unit_labels)
        miss_ess, miss_des = missing_skills(skill_ids, opp.get("skills", []), skill_labels)
        final = combine(float(g), float(s), float(i), weights)
        results.append({
            "opportunity_id": opp["id"],
            "title": opp.get("title"),
            "match_score": round(final, 4),            # e.g. 0.6317
            "match_percent": round(final * 100, 2),    # e.g. 63.17
            "breakdown": {
                "grade_score": round(float(g), 4),
                "skill_score": round(float(s), 4),
                "interest_score": round(float(i), 4),
            },
            "avg_requirement_mark": round(avg, 2),
            "meets_requirements": meets,
            "unmet_requirements": unmet,
            "missing_essential_skills": miss_ess,
            "missing_desirable_skills": miss_des,
            "interest_match": bool(i),
        })
    return rank(results)


# =============================================================================
# RecommendationEngine (UML class): database access + persistence
# =============================================================================

class RecommendationEngine:

    def __init__(self, model_path: str | None = None):
        self.model_type = MODEL_TYPE
        self.tfidf_vectorizer: TfidfTransformer | None = None  # units model, fitted in update_model()
        self.skill_vectorizer: TfidfTransformer | None = None  # skills model, fitted in update_model()
        self.cosine_similarity = cosine_similarity             # the similarity function used
        self.model_path = model_path                           # where engine.joblib lives
        self.model: dict | None = None                         # None = not fitted/loaded yet

    # ---- setup / persistence ----------------------------------------------------

    def init_app(self, app):
        self.model_path = app.config["ML_MODEL_PATH"]
        # Store the engine on the app so any code can reach it via get_engine().
        app.extensions["recommendation_engine"] = self
        # Load only from disk here, with no DB queries, so `flask db upgrade` works
        # on an empty database. A missing or stale model is refitted on first use.
        self.load()

    def load(self) -> bool:
        if not self.model_path or not os.path.exists(self.model_path):
            return False
        try:
            model = joblib.load(self.model_path)
        except Exception:  # corrupt or incompatible file: refit later
            log.warning("Could not load %s; it will be refitted", self.model_path, exc_info=True)
            self.model = None
            return False
        if "skill_vocabulary" not in model:
            # Saved by an older version (grades only). Not an error: it's refitted on first use.
            log.info("Model file %s is from an older version; it will be refitted", self.model_path)
            self.model = None
            return False
        self._set_model(model)
        return True

    def _save(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)  # create ml_models/ if needed
        # Write to a temp file then atomically replace, so a crash never leaves half a model.
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.model_path), suffix=".tmp")
        os.close(fd)
        try:
            joblib.dump(self.model, tmp)
            os.replace(tmp, self.model_path)   # swap the new file in, in one step
        finally:
            if os.path.exists(tmp):            # only still there if something failed
                os.remove(tmp)

    def _set_model(self, model: dict):
        self.model = model
        self.tfidf_vectorizer = model.get("transformer")
        self.skill_vectorizer = model.get("skill_transformer")

    def fitted_at(self) -> datetime | None:
        if not self.model:
            return None
        return datetime.fromisoformat(self.model["fitted_at"]).replace(tzinfo=None)

    # ---- database helpers ---------------------------------------------------------

    @staticmethod
    def _load_open_opportunities() -> list[dict]:
        # Imported inside the function so this module can be imported (e.g. by the
        # evaluation script) without needing the Flask app or database.
        from datetime import date

        from sqlalchemy import or_
        from sqlalchemy.orm import selectinload

        from app.models import (InternshipOpportunity, OpportunityPrecursor, OpportunitySkill,
                                OpportunityStatus)

        rows = (InternshipOpportunity.query
                .filter_by(status=OpportunityStatus.OPEN)
                .filter(or_(InternshipOpportunity.application_deadline.is_(None),
                            InternshipOpportunity.application_deadline >= date.today()))
                # selectinload fetches all related rows in a few queries up front,
                # instead of one extra query per opportunity.
                .options(selectinload(InternshipOpportunity.precursors)
                         .selectinload(OpportunityPrecursor.unit),
                         selectinload(InternshipOpportunity.skills)
                         .selectinload(OpportunitySkill.skill),
                         selectinload(InternshipOpportunity.partner),
                         selectinload(InternshipOpportunity.sector))
                .order_by(InternshipOpportunity.opportunity_id)
                .all())
        # Convert database objects into plain dictionaries.
        return [{
            "id": o.opportunity_id,
            "title": o.title,
            "sector_id": o.sector_id,
            "sector": o.sector.name if o.sector else None,
            "organization": o.partner.organization_name if o.partner else None,
            "requirements": [{
                "unit_id": p.unit_id,
                "importance": p.importance,
                "min_mark": None if p.min_mark is None else float(p.min_mark),
            } for p in o.precursors if p.unit.is_active],
            "skills": [{"skill_id": s.skill_id, "importance": s.importance}
                       for s in o.skills if s.skill.is_active],
        } for o in rows]

    # ---- UML: updateModel() ---------------------------------------------------------

    def update_model(self, opportunities: list[dict] | None = None) -> dict:
        data = opportunities if opportunities is not None else self._load_open_opportunities()
        self._set_model(build_model(data))
        self._save()
        log.info("Recommendation model fitted: %d opportunities, %d units, %d skills",
                 len(self.model["opportunity_ids"]), len(self.model["vocabulary"]),
                 len(self.model["skill_vocabulary"]))
        return self.model

    def ensure_fresh(self) -> list[dict]:
        data = self._load_open_opportunities()
        if self.model is None or self.model.get("fingerprint") != requirements_fingerprint(data):
            self.update_model(data)
        return data

    # ---- validation (TC04) ----------------------------------------------------------

    def validate_profile(self, student_id: int) -> dict[int, float]:
        from app.models import AcademicUnit, GradeProfile

        # The student's most recent grade submission (newest date; highest id if same time).
        profile = (GradeProfile.query.filter_by(student_id=student_id)
                   .order_by(GradeProfile.submission_date.desc(),
                             GradeProfile.profile_id.desc())
                   .first())
        # {unit_id: mark}; empty if the student has never submitted grades.
        marks = {g.unit_id: float(g.grade_value) for g in profile.grades} if profile else {}

        active = (AcademicUnit.query.filter_by(is_active=True)
                  .order_by(AcademicUnit.unit_name).all())

        # Which active units have no mark, and which have an impossible mark?
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

    def _score(self, student_id: int) -> list[dict]:
        from flask import current_app

        from app.extensions import db
        from app.models import AcademicUnit, Skill, Student

        # 1. Make sure the model matches the current open opportunities.
        opportunities = self.ensure_fresh()
        # 2. Check the grades. If incomplete this raises, BEFORE anything is written (TC04).
        marks = self.validate_profile(student_id)

        # 3. The student's selected skills and career interests (active ones only).
        student = db.session.get(Student, student_id)
        skill_ids = [s.skill_id for s in student.skills if s.skill.is_active]
        sector_ids = [i.sector_id for i in student.interests if i.sector.is_active]

        # 4. Score and rank. Names make "unmet requirements" and "missing skills" readable.
        unit_labels = {u.unit_id: u.unit_name for u in AcademicUnit.query.filter(
            AcademicUnit.unit_id.in_(self.model["vocabulary"]))}
        skill_labels = {s.skill_id: s.name for s in Skill.query.filter(
            Skill.skill_id.in_(self.model["skill_vocabulary"]))}
        weights = current_app.config.get("MATCH_WEIGHTS", DEFAULT_WEIGHTS)
        results = recommend(marks, self.model, unit_labels, skill_ids=skill_ids,
                            sector_ids=sector_ids, weights=weights, skill_labels=skill_labels)
        # Add organisation and sector (not needed for the maths, but shown to students).
        meta = {o["id"]: o for o in opportunities}
        for r in results:
            r["organization"] = meta[r["opportunity_id"]]["organization"]
            r["sector"] = meta[r["opportunity_id"]]["sector"]
        return results

    def score_student(self, student_id: int) -> dict[int, dict] | None:
        try:
            return {r["opportunity_id"]: r for r in self._score(student_id)}
        except IncompleteGradesError:
            return None

    def generate_recommendations(self, student_id: int, commit: bool = True) -> list[dict]:
        from app.extensions import db
        from app.models import Recommendation

        results = self._score(student_id)   # raises before anything is written (TC04)

        # 5. Replace the old rows with the new ones, so the student never ends up with
        #    half old / half new results.
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
                    grade_score=r["breakdown"]["grade_score"],
                    skill_score=r["breakdown"]["skill_score"],
                    interest_score=r["breakdown"]["interest_score"],
                    interest_match=r["interest_match"],
                    missing_skills={"essential": r["missing_essential_skills"],
                                    "desirable": r["missing_desirable_skills"]},
                    generated_at=generated_at,
                ))
            if commit:
                db.session.commit()      # make it permanent
            else:
                db.session.flush()       # the caller commits (or rolls back) everything
        except Exception:
            db.session.rollback()        # undo everything from this transaction
            raise                        # and pass the error on
        # The "Z" suffix marks the time as UTC for the frontend.
        for r in results:
            r["generated_at"] = generated_at.isoformat(timespec="seconds") + "Z"
        return results


def get_engine() -> RecommendationEngine:
    from flask import current_app   # the Flask app handling the current request
    return current_app.extensions["recommendation_engine"]
