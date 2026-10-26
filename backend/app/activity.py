"""Record events in the activity log.

log_activity() only ADDS the row to the current database transaction: it's saved by the same
commit as the change it describes (and disappears if that change is rolled back).
"""
from app.extensions import db
from app.models import ActivityLog


def _actor_id(actor):
    """Accepts a User, a Student / IndustryPartner / SystemAdmin row, a user id, or None."""
    if actor is None or isinstance(actor, int):
        return actor
    return getattr(actor, "user_id", None)


def log_activity(action: str, *, actor=None, target_type: str | None = None,
                 target_id: int | None = None, details: dict | None = None) -> None:
    db.session.add(ActivityLog(actor_user_id=_actor_id(actor), action=action,
                               target_type=target_type, target_id=target_id, details=details))


def log_and_commit(action: str, **kwargs) -> None:
    """For events with nothing else to save (e.g. a login or a model retrain)."""
    log_activity(action, **kwargs)
    db.session.commit()
