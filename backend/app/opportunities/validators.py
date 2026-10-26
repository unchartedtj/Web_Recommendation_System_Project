"""Validation for creating and editing internship opportunities.

Returns (cleaned_data, errors) like the auth validators. Per-row requirement errors
use keys "requirements.<index>.<field>" so the form can show them on the right row.
Example: {"requirements.1.unit_id": "This unit is already listed"} means the 2nd row
(rows are counted from 0) chose a unit that an earlier row already uses.
"""
from datetime import date

from app.counties import canonical_county
from app.models import RequirementImportance

MIN_REQUIREMENTS, MAX_REQUIREMENTS = 2, 5     # unit requirements per opportunity
MIN_SKILLS, MAX_SKILLS = 1, 8                 # required skills per opportunity
# Required text fields and their maximum lengths (matching the database columns).
# (The sector is no longer text: it's chosen from the preset list as sector_id.)
TEXT_FIELDS = {"title": 200, "description": 5000, "location": 150}


def _to_int(value):
    """Parse an int from a JSON number or numeric string; None if not possible.
    e.g. 3 → 3, "3" → 3, "3.0" → 3, "3.5" → None, "abc" → None."""
    if isinstance(value, bool):  # bool is a subclass of int; reject True/False
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else None


def _to_number(value):
    """Parse any number (decimals allowed); None if not possible."""
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate_opportunity(data: dict, active_unit_ids: set[int], active_skill_ids: set[int],
                         active_sector_ids: set[int]) -> tuple[dict, dict]:
    """Check the whole opportunity form. Collects ALL errors, not just the first one.

    The active_* sets are the ids partners may choose from (loaded from the database
    by the route), so this function itself never touches the database.
    """
    errors: dict[str, str] = {}
    cleaned: dict = {}

    # Title, description, location: required, trimmed, not too long.
    for field, max_len in TEXT_FIELDS.items():
        value = data.get(field)
        value = value.strip() if isinstance(value, str) else ""
        if not value:
            errors[field] = "This field is required"
        elif len(value) > max_len:
            errors[field] = f"Must be at most {max_len} characters"
        cleaned[field] = value

    # Location: must be one of Kenya's 47 counties (chosen from the dropdown).
    if "location" not in errors:
        county = canonical_county(cleaned["location"])
        if county is None:
            errors["location"] = "Choose a county from the list"
        else:
            cleaned["location"] = county

    duration = _to_int(data.get("duration_months"))
    if duration is None or not 1 <= duration <= 12:
        errors["duration_months"] = "Duration must be a whole number of months from 1 to 12"
    cleaned["duration_months"] = duration

    slots = _to_int(data.get("slots"))
    if slots is None or slots < 1:
        errors["slots"] = "Slots must be a whole number, at least 1"
    cleaned["slots"] = slots

    try:
        # fromisoformat reads "2026-11-29" into a date; anything else raises ValueError.
        deadline = date.fromisoformat(str(data.get("application_deadline") or ""))
        if deadline <= date.today():
            errors["application_deadline"] = "Deadline must be a future date"
        cleaned["application_deadline"] = deadline
    except ValueError:
        errors["application_deadline"] = "Enter a valid date (YYYY-MM-DD)"

    # Sector: required, and must be one of the active preset sectors.
    sector_id = _to_int(data.get("sector_id"))
    if sector_id is None:
        errors["sector_id"] = "Choose a sector"
    elif sector_id not in active_sector_ids:
        errors["sector_id"] = "Unknown or inactive sector"
    cleaned["sector_id"] = sector_id

    cleaned["requirements"] = _validate_requirements(data.get("requirements"),
                                                     active_unit_ids, errors)
    cleaned["skills"] = _validate_skills(data.get("skills"), active_skill_ids, errors)
    return cleaned, errors


def _validate_skills(raw, active_skill_ids: set[int], errors: dict) -> list[dict]:
    """Check the required-skills list: 1 to 8 skills, at least one essential, no duplicates,
    all active. Per-row errors use keys like "skills.2.skill_id"."""
    if not isinstance(raw, list) or not raw:
        errors["skills"] = f"Add between {MIN_SKILLS} and {MAX_SKILLS} required skills"
        return []
    if len(raw) > MAX_SKILLS:
        errors["skills"] = f"An opportunity can require at most {MAX_SKILLS} skills"

    cleaned, seen = [], set()
    for i, row in enumerate(raw):
        prefix = f"skills.{i}"
        row = row if isinstance(row, dict) else {}

        skill_id = _to_int(row.get("skill_id"))
        if skill_id is None:
            errors[f"{prefix}.skill_id"] = "Choose a skill"
        elif skill_id not in active_skill_ids:
            errors[f"{prefix}.skill_id"] = "Unknown or inactive skill"
        elif skill_id in seen:
            errors[f"{prefix}.skill_id"] = "This skill is already listed"
        seen.add(skill_id)

        importance = row.get("importance") or RequirementImportance.ESSENTIAL
        if importance not in RequirementImportance.ALL:
            errors[f"{prefix}.importance"] = "Importance must be 'essential' or 'desirable'"
        cleaned.append({"skill_id": skill_id, "importance": importance})

    if not any(s["importance"] == RequirementImportance.ESSENTIAL for s in cleaned) \
            and "skills" not in errors:
        errors["skills"] = "At least one required skill must be essential"
    return cleaned


def _validate_requirements(raw, active_unit_ids: set[int], errors: dict) -> list[dict]:
    """Check the requirements list. Adds any problems to `errors` (the same dict the
    caller uses) and returns the cleaned list."""
    if not isinstance(raw, list):
        errors["requirements"] = "Add between 2 and 5 required units"
        return []
    if not MIN_REQUIREMENTS <= len(raw) <= MAX_REQUIREMENTS:
        errors["requirements"] = (f"An opportunity must have between {MIN_REQUIREMENTS} "
                                  f"and {MAX_REQUIREMENTS} required units")

    cleaned, seen = [], set()   # `seen` remembers units already used, to catch duplicates
    for i, row in enumerate(raw):
        prefix = f"requirements.{i}"          # e.g. "requirements.0" for the first row
        row = row if isinstance(row, dict) else {}

        # --- Unit: must be chosen, must exist and be active, must not repeat ---
        unit_id = _to_int(row.get("unit_id"))
        if unit_id is None:
            errors[f"{prefix}.unit_id"] = "Choose a unit"
        elif unit_id not in active_unit_ids:
            errors[f"{prefix}.unit_id"] = "Unknown or inactive unit"
        elif unit_id in seen:
            errors[f"{prefix}.unit_id"] = "This unit is already listed"
        seen.add(unit_id)

        # --- Importance: essential (the default if not given) or desirable ---
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

    # At least one row must be essential (only reported if the row count itself was OK,
    # so the partner sees one list-level message at a time).
    if raw and not any(r["importance"] == RequirementImportance.ESSENTIAL for r in cleaned) \
            and "requirements" not in errors:
        errors["requirements"] = "At least one requirement must be essential"
    return cleaned
