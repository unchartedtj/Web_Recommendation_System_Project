"""Validation for creating and editing internship opportunities.

Returns (cleaned_data, errors) like the auth validators. Per-row requirement errors
use keys "requirements.<index>.<field>" so the form can show them on the right row.
"""
from datetime import date

from app.models import RequirementImportance

MIN_REQUIREMENTS, MAX_REQUIREMENTS = 2, 5
TEXT_FIELDS = {"title": 200, "description": 5000, "sector": 100, "location": 150}


def _to_int(value):
    """Parse an int from a JSON number or numeric string; None if not possible."""
    if isinstance(value, bool):  # bool is a subclass of int; reject True/False
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else None


def _to_number(value):
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate_opportunity(data: dict, active_unit_ids: set[int]) -> tuple[dict, dict]:
    errors: dict[str, str] = {}
    cleaned: dict = {}

    for field, max_len in TEXT_FIELDS.items():
        value = data.get(field)
        value = value.strip() if isinstance(value, str) else ""
        if not value:
            errors[field] = "This field is required"
        elif len(value) > max_len:
            errors[field] = f"Must be at most {max_len} characters"
        cleaned[field] = value

    duration = _to_int(data.get("duration_months"))
    if duration is None or not 1 <= duration <= 12:
        errors["duration_months"] = "Duration must be a whole number of months from 1 to 12"
    cleaned["duration_months"] = duration

    slots = _to_int(data.get("slots"))
    if slots is None or slots < 1:
        errors["slots"] = "Slots must be a whole number, at least 1"
    cleaned["slots"] = slots

    try:
        deadline = date.fromisoformat(str(data.get("application_deadline") or ""))
        if deadline <= date.today():
            errors["application_deadline"] = "Deadline must be a future date"
        cleaned["application_deadline"] = deadline
    except ValueError:
        errors["application_deadline"] = "Enter a valid date (YYYY-MM-DD)"

    cleaned["requirements"] = _validate_requirements(data.get("requirements"),
                                                     active_unit_ids, errors)
    return cleaned, errors


def _validate_requirements(raw, active_unit_ids: set[int], errors: dict) -> list[dict]:
    if not isinstance(raw, list):
        errors["requirements"] = "Add between 2 and 5 required units"
        return []
    if not MIN_REQUIREMENTS <= len(raw) <= MAX_REQUIREMENTS:
        errors["requirements"] = (f"An opportunity must have between {MIN_REQUIREMENTS} "
                                  f"and {MAX_REQUIREMENTS} required units")

    cleaned, seen = [], set()
    for i, row in enumerate(raw):
        prefix = f"requirements.{i}"
        row = row if isinstance(row, dict) else {}

        unit_id = _to_int(row.get("unit_id"))
        if unit_id is None:
            errors[f"{prefix}.unit_id"] = "Choose a unit"
        elif unit_id not in active_unit_ids:
            errors[f"{prefix}.unit_id"] = "Unknown or inactive unit"
        elif unit_id in seen:
            errors[f"{prefix}.unit_id"] = "This unit is already listed"
        seen.add(unit_id)

        importance = row.get("importance") or RequirementImportance.ESSENTIAL
        if importance not in RequirementImportance.ALL:
            errors[f"{prefix}.importance"] = "Importance must be 'essential' or 'desirable'"

        # min_mark is optional: null, missing or "" means no minimum.
        min_mark = row.get("min_mark")
        if min_mark in (None, ""):
            min_mark = None
        else:
            min_mark = _to_number(min_mark)
            if min_mark is None or not 0 <= min_mark <= 100:
                errors[f"{prefix}.min_mark"] = "Minimum mark must be between 0 and 100"

        cleaned.append({"unit_id": unit_id, "importance": importance, "min_mark": min_mark})

    if raw and not any(r["importance"] == RequirementImportance.ESSENTIAL for r in cleaned) \
            and "requirements" not in errors:
        errors["requirements"] = "At least one requirement must be essential"
    return cleaned
