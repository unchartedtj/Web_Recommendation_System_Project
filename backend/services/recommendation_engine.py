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

Worked mini example (2 opportunities, 3 units)
----------------------------------------------
    Opportunity A requires: OOP (essential), Databases (desirable)
    Opportunity B requires: Databases (essential), Networks (essential)
    n = 2 opportunities. Databases is needed by both (df=2); OOP and Networks by one (df=1).
    idf(OOP) = idf(Networks) = ln(3/2) + 1 = 1.405     idf(Databases) = ln(3/3) + 1 = 1.0
    A's vector = [2 x 1.405, 1 x 1.0, 0]  over [OOP, Databases, Networks]
    B's vector = [0, 2 x 1.0, 2 x 1.405]
    A student with OOP 90, Databases 60, Networks 40 has the vector
        [0.90 x 1.405, 0.60 x 1.0, 0.40 x 1.405]
    and cosine similarity then says how closely the student's "shape" of strengths
    points in the same direction as each opportunity's requirements.

The maths is kept in pure functions (build_model, build_student_vector, score,
evaluate_requirements, rank, recommend) that take plain Python data, so they can be
unit tested and used by evaluation/evaluate_engine.py without a database.
The RecommendationEngine class wraps them with database access and model persistence.
"""
# Lets us write type hints like `list | None` on older Python versions.
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
MODEL_TYPE = "TF-IDF + Cosine Similarity"
# How much each importance level counts in an opportunity's vector.
# Essential counts double, so it pulls the score more than desirable does.
IMPORTANCE_WEIGHTS = {"essential": 2.0, "desirable": 1.0}


class IncompleteGradesError(Exception):
    """The student's grade profile can't be scored (TC04). Nothing is written.

    `missing` = units with no mark; `invalid` = units with a mark outside 0-100.
    The API turns this into a 400 response listing those units.
    """

    def __init__(self, missing: list | None = None, invalid: list | None = None):
        self.missing = missing or []   # `or []` turns None into an empty list
        self.invalid = invalid or []
        super().__init__(
            f"Grade profile is incomplete: {len(self.missing)} missing, "
            f"{len(self.invalid)} invalid unit(s)"
        )


# =============================================================================
# Pure functions (no database)
# =============================================================================

def requirements_fingerprint(opportunities: list[dict]) -> str:
    """Hash of the requirement structure. If it changes, the fitted model is stale.

    We put every (opportunity, unit, importance, min mark) into a fixed, sorted order,
    turn it into text and hash it. Same requirements → same hash; ANY change → different
    hash. Comparing two short hashes is much cheaper than comparing all the data.
    """
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
    # Sort by id so row i of the matrix always means the same opportunity.
    opps = sorted(opportunities, key=lambda o: o["id"])
    # The vocabulary = every unit required by at least one open opportunity.
    # A set {...} removes duplicates; sorted() fixes the column order.
    vocabulary = sorted({r["unit_id"] for o in opps for r in o["requirements"]})

    # Start with an "empty" model; the real values are filled in below.
    model = {
        "model_type": MODEL_TYPE,
        "vocabulary": vocabulary,                              # column j = unit vocabulary[j]
        "idf": np.zeros(len(vocabulary)),                      # one IDF weight per unit
        "opportunity_ids": [o["id"] for o in opps],            # row i = opportunity_ids[i]
        "opportunities": opps,                                 # kept for titles/requirements
        "opp_vectors": np.zeros((len(opps), len(vocabulary))), # the opportunity x unit matrix
        "transformer": None,                                   # the fitted sklearn object
        "fingerprint": requirements_fingerprint(opps),         # used to detect staleness
        "fitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if not opps or not vocabulary:
        return model  # nothing open to recommend; sklearn can't fit an empty matrix

    # col maps a unit_id to its column number, e.g. {4: 0, 7: 1, 9: 2}.
    col = {unit_id: j for j, unit_id in enumerate(vocabulary)}

    # Fill the importance matrix: weights[row, column] = 2 (essential) or 1 (desirable).
    # Cells for units an opportunity doesn't need stay 0.
    weights = np.zeros((len(opps), len(vocabulary)))
    for i, opp in enumerate(opps):
        for req in opp["requirements"]:
            weights[i, col[req["unit_id"]]] = IMPORTANCE_WEIGHTS[req["importance"]]

    # IDF is learnt from whether a unit is required at all (binary), not from its
    # importance, so "how many opportunities need this unit" is all that affects rarity.
    # (weights > 0) gives True/False; .astype(float) turns that into 1.0/0.0.
    binary = (weights > 0).astype(float)
    # norm=None: don't rescale rows; smooth_idf=True: the "+1" smoothing in the formula.
    transformer = TfidfTransformer(smooth_idf=True, norm=None).fit(binary)

    model["idf"] = transformer.idf_.copy()                # the learnt IDF weight per unit
    # numpy multiplies each column by that unit's IDF weight ("broadcasting").
    model["opp_vectors"] = weights * transformer.idf_
    model["transformer"] = transformer
    return model


def build_student_vector(marks: dict[int, float], model: dict) -> np.ndarray:
    """mark / 100 x idf for every vocabulary unit.

    Example: mark 80 in a unit with idf 1.69 → 0.80 x 1.69 = 1.35.
    Raises IncompleteGradesError if a vocabulary unit has no mark or an out-of-range mark.
    """
    missing = [u for u in model["vocabulary"] if u not in marks]
    invalid = [u for u in model["vocabulary"]
               if u in marks and not 0 <= float(marks[u]) <= 100]
    if missing or invalid:
        raise IncompleteGradesError(missing, invalid)
    # Marks in the same column order as the vocabulary, scaled to 0-1.
    raw = np.array([float(marks[u]) / 100.0 for u in model["vocabulary"]])
    return raw * model["idf"]   # element-by-element multiply with the IDF weights


def score(student_vector: np.ndarray, model: dict) -> np.ndarray:
    """Cosine similarity between the student and every opportunity (0 to 1).

    Cosine similarity measures the ANGLE between two vectors: 1 = pointing the same
    way (the student is strong exactly where the opportunity needs), 0 = no overlap.
    """
    if len(model["opportunity_ids"]) == 0:
        return np.array([])
    # sklearn expects 2-D input, so reshape(1, -1) turns the vector into a 1-row matrix.
    # The result is a 1 x N matrix (one score per opportunity); [0] takes that single row.
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
    """Order results and assign ranks 1..N.

    Order: eligible (meets_requirements) first, then match_score descending,
    then avg_requirement_mark descending (tie-breaker), then opportunity_id for stability.
    Scores are compared at 4 decimal places (as stored), so float noise can't break a real tie.
    """
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
              unit_labels: dict[int, str] | None = None) -> list[dict]:
    """Score and rank every opportunity in the model for one student.

    This is the whole pipeline in one call: student vector → cosine scores →
    minimum-mark checks → ranking.
    """
    if not model["opportunity_ids"]:
        return []   # no open opportunities → nothing to recommend
    scores = score(build_student_vector(marks, model), model)
    results = []
    # zip pairs each opportunity with its score (same order as the matrix rows).
    for opp, s in zip(model["opportunities"], scores):
        meets, unmet, avg = evaluate_requirements(marks, opp["requirements"], unit_labels)
        results.append({
            "opportunity_id": opp["id"],
            "title": opp.get("title"),
            "match_score": round(float(s), 4),          # e.g. 0.6317
            "match_percent": round(float(s) * 100, 2),  # e.g. 63.17
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

    One instance is created when the app starts (app/extensions.py) and shared by
    every request. It keeps the fitted model in memory (self.model) and on disk.
    """

    def __init__(self, model_path: str | None = None):
        self.model_type = MODEL_TYPE
        self.tfidf_vectorizer: TfidfTransformer | None = None  # fitted in update_model()
        self.cosine_similarity = cosine_similarity             # the similarity function used
        self.model_path = model_path                           # where engine.joblib lives
        self.model: dict | None = None                         # None = not fitted/loaded yet

    # ---- setup / persistence ----------------------------------------------------

    def init_app(self, app):
        """Called by create_app(): connect the engine to the Flask app."""
        self.model_path = app.config["ML_MODEL_PATH"]
        # Store the engine on the app so any code can reach it via get_engine().
        app.extensions["recommendation_engine"] = self
        # Load only from disk here, with no DB queries, so `flask db upgrade` works
        # on an empty database. A missing or stale model is refitted on first use.
        self.load()

    def load(self) -> bool:
        """Load the saved model from engine.joblib. Returns True if it worked."""
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
        """Save the current model to engine.joblib."""
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

    # ---- database helpers ---------------------------------------------------------

    @staticmethod
    def _load_open_opportunities() -> list[dict]:
        """Open opportunities as plain dicts (the input format of build_model).

        Requirements on INACTIVE units are ignored: students can't submit grades
        for them, so they can't be scored.
        """
        # Imported inside the function so this module can be imported (e.g. by the
        # evaluation script) without needing the Flask app or database.
        from sqlalchemy.orm import selectinload

        from app.models import InternshipOpportunity, OpportunityPrecursor, OpportunityStatus

        rows = (InternshipOpportunity.query
                .filter_by(status=OpportunityStatus.OPEN)
                # selectinload fetches all requirements, their units and the partners in a
                # few queries up front, instead of one extra query per opportunity.
                .options(selectinload(InternshipOpportunity.precursors)
                         .selectinload(OpportunityPrecursor.unit),
                         selectinload(InternshipOpportunity.partner))
                .order_by(InternshipOpportunity.opportunity_id)
                .all())
        # Convert database objects into plain dictionaries.
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
        """Refit on all OPEN opportunities and save to disk ("training").

        Called after every opportunity create/edit/close, by `flask seed-data`,
        and by the admin retrain endpoint.
        """
        data = opportunities if opportunities is not None else self._load_open_opportunities()
        self._set_model(build_model(data))
        self._save()
        log.info("Recommendation model fitted: %d opportunities, %d units",
                 len(self.model["opportunity_ids"]), len(self.model["vocabulary"]))
        return self.model

    def ensure_fresh(self) -> list[dict]:
        """Refit if the model is missing or no longer matches the database.

        Safety net: normally the model is refitted after every change, but if a change
        happened some other way (e.g. directly in phpMyAdmin), the fingerprints differ
        and we refit here before scoring.
        """
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
        """UML name for rank(); kept so the class matches the diagram."""
        return rank(results)

    # ---- UML: generateRecommendations(studentId) ------------------------------------

    def generate_recommendations(self, student_id: int) -> list[dict]:
        """Validate, score and rank, then replace the student's saved recommendations
        in one transaction. Returns the ranked list."""
        from app.extensions import db
        from app.models import AcademicUnit, Recommendation

        # 1. Make sure the model matches the current open opportunities.
        opportunities = self.ensure_fresh()
        # 2. Check the grades. If incomplete this raises, BEFORE anything is written (TC04).
        marks = self.validate_profile(student_id)

        # 3. Score and rank. Unit names make the "unmet requirements" readable.
        labels = {u.unit_id: u.unit_name
                  for u in AcademicUnit.query.filter(
                      AcademicUnit.unit_id.in_(self.model["vocabulary"]))}
        results = recommend(marks, self.model, labels)
        # Add organisation and sector (not needed for the maths, but shown to students).
        meta = {o["id"]: o for o in opportunities}
        for r in results:
            r["organization"] = meta[r["opportunity_id"]]["organization"]
            r["sector"] = meta[r["opportunity_id"]]["sector"]

        # 4. Save: delete the old rows and insert the new ones in ONE transaction,
        #    so the student never ends up with half old / half new results.
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
            db.session.commit()      # make it permanent
        except Exception:
            db.session.rollback()    # undo everything from this transaction
            raise                    # and pass the error on
        # The "Z" suffix marks the time as UTC for the frontend.
        for r in results:
            r["generated_at"] = generated_at.isoformat(timespec="seconds") + "Z"
        return results


def get_engine() -> RecommendationEngine:
    """The app's shared engine instance (created in create_app)."""
    from flask import current_app   # the Flask app handling the current request
    return current_app.extensions["recommendation_engine"]
