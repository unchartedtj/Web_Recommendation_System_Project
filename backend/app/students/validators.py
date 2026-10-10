"""Validation for the student profile (test case TC04).

A profile = a mark for every active unit + 1 to 10 skills + 1 to 3 career interests.
Every problem is collected, keyed by field, so the frontend can show them all at once:
    "grades"            list-level message, e.g. which units are missing
    "grades.<unit_id>"  a problem with one unit's mark (missing, not a number, out of range...)
    "skill_ids"         wrong number of skills, duplicates, or unknown/inactive skills
    "sector_ids"        same, for career interests
"""
from decimal import Decimal, InvalidOperation

MIN_SKILLS, MAX_SKILLS = 1, 10        # the cap stops students ticking everything
MIN_INTERESTS, MAX_INTERESTS = 1, 3


def _parse_mark(value):
    """Return (mark as float, error message or None).

    A mark must be a number from 0 to 100 with at most 2 decimal places.
    Decimal(str(...)) is used to count decimals exactly: 100.555 has 3, so it's rejected.
    """
    if isinstance(value, bool) or value is None or value == "":
        return None, "Enter a mark"
    try:
        dec = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None, "Mark must be a number"
    if not dec.is_finite():
        return None, "Mark must be a number"
    if not Decimal(0) <= dec <= Decimal(100):
        return None, "Mark must be between 0 and 100"
    if dec.as_tuple().exponent < -2:          # exponent -3 means 3 decimal places
        return None, "Mark can have at most 2 decimal places"
    return float(dec), None


def _parse_id_list(raw, field: str, active_ids: set[int], low: int, high: int,
                   noun: str, errors: dict) -> list[int]:
    """Check a list of ids (skills or sectors): length low..high, no duplicates, all active."""
    if not isinstance(raw, list):
        errors[field] = f"Choose between {low} and {high} {noun}"
        return []
    ids, problems = [], []
    for value in raw:
        try:
            if isinstance(value, bool):
                raise ValueError
            ids.append(int(value))
        except (TypeError, ValueError):
            problems.append(f"invalid id {value!r}")
    if len(set(ids)) != len(ids):
        problems.append("duplicates are not allowed")
    unknown = sorted({i for i in ids if i not in active_ids})
    if unknown:
        problems.append(f"unknown or inactive id(s) {unknown}")
    count = len(set(ids))
    if not low <= count <= high:
        # The count message comes first; it's the most common mistake.
        problems.insert(0, f"choose between {low} and {high} {noun} (you chose {count})")
    if problems:
        message = "; ".join(problems)
        errors[field] = message[0].upper() + message[1:]
    return sorted(set(ids))


def validate_profile(data: dict, active_units: dict[int, str], active_skill_ids: set[int],
                     active_sector_ids: set[int]) -> tuple[dict, dict, bool]:
    """Check a profile submission.

    active_units is {unit_id: unit_name} for every active unit (all of them need a mark).
    Returns (cleaned, errors, implausible):
      cleaned     = {"grades": {unit_id: mark}, "skill_ids": [...], "sector_ids": [...]}
      errors      = {field: message}; empty when everything is valid
      implausible = True when all marks are identical (the caller decides what to do)
    """
    errors: dict[str, str] = {}

    # ---- Grades ----
    raw_grades = data.get("grades")
    if not isinstance(raw_grades, dict):
        raw_grades = {}
        errors["grades"] = "Enter a mark for every unit"
    grades: dict[int, float] = {}
    for key, value in raw_grades.items():
        try:
            unit_id = int(key)          # JSON keys are always text, e.g. "5" → 5
        except (TypeError, ValueError):
            errors[f"grades.{key}"] = "Unknown unit"
            continue
        if unit_id not in active_units:
            errors[f"grades.{key}"] = "Unknown or inactive unit"
            continue
        mark, problem = _parse_mark(value)
        if problem:
            errors[f"grades.{unit_id}"] = problem
        else:
            grades[unit_id] = mark

    # Units with no mark at all (not even an invalid one).
    missing = [uid for uid in active_units
               if str(uid) not in {str(k) for k in raw_grades} and uid not in grades]
    for uid in missing:
        errors.setdefault(f"grades.{uid}", "Enter a mark")
    if missing:
        names = ", ".join(sorted(active_units[uid] for uid in missing))
        errors["grades"] = f"Enter a mark for every unit. Missing: {names}"

    # ---- Skills and interests ----
    skill_ids = _parse_id_list(data.get("skill_ids"), "skill_ids", active_skill_ids,
                               MIN_SKILLS, MAX_SKILLS, "skills", errors)
    sector_ids = _parse_id_list(data.get("sector_ids"), "sector_ids", active_sector_ids,
                                MIN_INTERESTS, MAX_INTERESTS, "career interests", errors)

    # "Implausible entry": every unit has exactly the same mark (e.g. all 70). Probably a
    # lazy or test entry, so the student is asked to confirm (limitation mitigation 1.7).
    implausible = (not errors and len(grades) == len(active_units) > 1
                   and len(set(grades.values())) == 1)

    return {"grades": grades, "skill_ids": skill_ids, "sector_ids": sector_ids}, errors, implausible
