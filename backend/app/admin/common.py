"""Small helpers shared by the admin endpoints: pagination, query parameters, dates and CSV."""
import csv
import io

from flask import Response, request

from app.errors import ApiError
from app.utils import int_arg, iso, parse_date  # noqa: F401 (re-exported)

ADMIN = "system_admin"
DEFAULT_PER_PAGE, MAX_PER_PAGE = 20, 100


def str_arg(name: str) -> str:
    return request.args.get(name, "").strip()


def choice_arg(name: str, allowed) -> str | None:
    value = str_arg(name)
    if not value:
        return None
    if value not in allowed:
        raise ApiError(f"Unknown {name}", 400, {name: f"Must be one of {', '.join(allowed)}"})
    return value


def bool_arg(name: str) -> bool | None:
    value = str_arg(name).lower()
    if not value:
        return None
    if value in ("true", "1", "yes"):
        return True
    if value in ("false", "0", "no"):
        return False
    raise ApiError(f"{name} must be true or false", 400, {name: "Must be true or false"})


def page_params() -> tuple[int, int]:
    return (int_arg("page", 1, minimum=1),
            int_arg("per_page", DEFAULT_PER_PAGE, minimum=1, maximum=MAX_PER_PAGE))


def paginate(query, serialize) -> dict:
    """Run a SQLAlchemy query one page at a time: {items, page, per_page, total, pages}."""
    page, per_page = page_params()
    total = query.order_by(None).count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()
    return {"items": [serialize(r) for r in rows], "page": page, "per_page": per_page,
            "total": total, "pages": max(1, -(-total // per_page))}


def paginate_list(items: list) -> dict:
    """Same shape as paginate(), for lists already built in Python (e.g. filtered by a
    property the database can't check, like "profile complete")."""
    page, per_page = page_params()
    start = (page - 1) * per_page
    return {"items": items[start:start + per_page], "page": page, "per_page": per_page,
            "total": len(items), "pages": max(1, -(-len(items) // per_page))}


def csv_response(filename: str, header: list[str], rows) -> Response:
    """Send rows as a downloadable CSV file."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return Response(buffer.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
