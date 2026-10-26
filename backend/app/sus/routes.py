"""The usability questionnaire for students and industry partners.

    GET /api/sus/questions   the 10 statements and the answer scale (any logged-in user)
    GET /api/sus/mine        my saved answers, or null
    PUT /api/sus             submit or update my answers {q1..q10: 1-5, comments?}

The score is calculated and stored, but never shown to the person answering.
"""
from datetime import datetime, timezone

from flask import jsonify, request
from flask_jwt_extended import jwt_required

from app.activity import log_activity
from app.auth.decorators import current_user, role_required
from app.errors import ApiError
from app.extensions import db
from app.models import SusResponse
from app.sus import sus_bp
from app.sus.questions import SCALE, SUS_QUESTIONS
from app.sus.services import sus_score

RESPONDENTS = ("student", "industry_partner")
COMMENTS_MAX = 1000


def _mine_json(r: SusResponse | None):
    if r is None:
        return None
    return {**{f"q{i}": getattr(r, f"q{i}") for i in range(1, 11)}, "comments": r.comments,
            "updated_at": r.updated_at.isoformat(timespec="seconds") + "Z" if r.updated_at else None}


@sus_bp.get("/questions")
@jwt_required()
def questions():
    return jsonify({"questions": SUS_QUESTIONS, "scale": SCALE})


@sus_bp.get("/mine")
@role_required(*RESPONDENTS)
def mine():
    user = current_user()
    return jsonify({"response": _mine_json(SusResponse.query.filter_by(user_id=user.user_id).first())})


@sus_bp.put("")
@role_required(*RESPONDENTS)
def submit():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object", 400)

    errors, answers = {}, []
    for i in range(1, 11):
        value = data.get(f"q{i}")
        # bool is a kind of int in Python, so exclude it explicitly.
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
            errors[f"q{i}"] = "Please choose an answer from 1 to 5"
        answers.append(value)
    comments = data.get("comments")
    if comments is not None and not isinstance(comments, str):
        errors["comments"] = "Must be text"
    comments = (comments or "").strip() or None if isinstance(comments, (str, type(None))) else None
    if comments and len(comments) > COMMENTS_MAX:
        errors["comments"] = f"At most {COMMENTS_MAX} characters"
    if errors:
        raise ApiError("Please answer all 10 statements", 400, errors)

    user = current_user()
    response = SusResponse.query.filter_by(user_id=user.user_id).first()
    created = response is None
    if created:
        response = SusResponse(user_id=user.user_id, role=user.role.value)
        db.session.add(response)
    for i, value in enumerate(answers, start=1):
        setattr(response, f"q{i}", value)
    response.sus_score = sus_score(answers)
    response.comments = comments
    response.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.flush()
    log_activity("sus.submitted" if created else "sus.updated", actor=user,
                 target_type="sus_response", target_id=response.response_id)
    db.session.commit()
    # Thank the user; the score itself is deliberately NOT returned.
    return jsonify({"message": "Thank you for your feedback!", "response": _mine_json(response)}), \
        201 if created else 200
