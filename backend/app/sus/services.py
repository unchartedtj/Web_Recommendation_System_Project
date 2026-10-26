"""SUS scoring and the summary shown on the admin "SUS Results" page.

Standard scoring: each odd item contributes (answer - 1), each even item (5 - answer);
the sum (0-40) times 2.5 gives a score from 0 to 100.
    all answers 3            → 50
    odd all 5, even all 1    → 100 (best)
    odd all 1, even all 5    → 0   (worst)
"""
from app.models import SusResponse
from app.sus.questions import SUS_QUESTIONS, TARGET_SCORE


def sus_score(answers: list[int]) -> float:
    """answers = the 10 answers in order (q1..q10), each 1-5."""
    if len(answers) != 10:
        raise ValueError("SUS needs exactly 10 answers")
    total = 0
    for number, answer in enumerate(answers, start=1):
        total += (answer - 1) if number % 2 == 1 else (5 - answer)
    return total * 2.5


def _mean(values) -> float | None:
    values = list(values)
    return round(sum(values) / len(values), 2) if values else None


def summary() -> dict:
    """Everything the admin results page needs, computed from all responses."""
    rows = SusResponse.query.all()
    scores = [r.sus_score for r in rows]
    by_role = {}
    for r in rows:
        by_role.setdefault(r.role, []).append(r.sus_score)

    # Distribution in buckets of 10: "0-9", "10-19", ..., "90-100".
    buckets = [{"range": f"{lo}-{lo + 9}" if lo < 90 else "90-100", "count": 0}
               for lo in range(0, 100, 10)]
    for s in scores:
        buckets[min(int(s // 10), 9)]["count"] += 1

    mean = _mean(scores)
    return {
        "count": len(rows),
        "mean": mean,
        "min": min(scores) if scores else None,
        "max": max(scores) if scores else None,
        "target": TARGET_SCORE,
        "meets_target": mean is not None and mean >= TARGET_SCORE,
        "by_role": {role: {"count": len(v), "mean": _mean(v)} for role, v in by_role.items()},
        "items": [{"number": i, "statement": SUS_QUESTIONS[i - 1],
                   "average": _mean(getattr(r, f"q{i}") for r in rows)} for i in range(1, 11)],
        "distribution": buckets,
    }
