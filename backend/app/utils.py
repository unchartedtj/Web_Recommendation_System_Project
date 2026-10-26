"""Small helpers shared by many route and service files (one copy instead of several)."""
from datetime import date, datetime

from flask import request

from app.errors import ApiError


def json_body() -> dict:
    """Read the request body as JSON. Anything that isn't a JSON object → 400."""
    data = request.get_json(silent=True)   # silent=True: return None instead of crashing
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object", 400)
    return data


def iso(value) -> str | None:
    """Dates → "2026-10-15"; datetimes → "2026-10-15T09:30:00Z" (UTC); None stays None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds") + "Z"
    return value.isoformat()


def parse_date(value, field: str, errors: dict):
    """"2027-01-31" → date. Empty → None. Anything else → adds a field error, returns None."""
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        errors[field] = "Use the format YYYY-MM-DD"
        return None


def int_arg(name: str, default=None, minimum: int | None = None, maximum: int | None = None):
    """Read an optional whole number from the query string (e.g. ?sector_id=3). Bad value → 400."""
    raw = request.args.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ApiError(f"{name} must be a number", 400, {name: "Must be a number"})
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value
