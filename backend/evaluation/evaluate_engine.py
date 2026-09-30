"""Offline evaluation of the recommendation engine (for Chapter 5).

Run from the backend folder:
    python -m evaluation.evaluate_engine

The script builds labelled synthetic students and checks whether the engine recommends
the internship each student was designed for. It uses the seeded demo opportunities
(app/seed/catalog.py) and the pure engine functions, so it needs NO database.

Synthetic data (fixed seed, so results are reproducible):
- 30 standard students, 6 per opportunity: marks 75-95 in the target opportunity's
  ESSENTIAL units, and 40-70 in every other catalogue unit (including the target's
  desirable units).
- 5 borderline students, strong (75-95) in the essential units of TWO opportunities.
  Either one counts as correct.

Metrics:
- Top-1 accuracy: the expected internship is ranked #1.
- Top-3 accuracy: the expected internship is in the top 3.
"""
import csv
import os
import random

from app.seed import catalog
from services.recommendation_engine import build_model, recommend

SEED = 42
PER_OPPORTUNITY = 6
HIGH, LOW = (75, 95), (40, 70)
BORDERLINE_PAIRS = [("SWE", "WEB"), ("WEB", "DATA"), ("DATA", "BA"), ("NET", "SWE"), ("BA", "SWE")]
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results.csv")

# Plain-data model inputs. Unit ids are 1..12 and opportunity ids 1..5, in catalogue order.
UNIT_IDS = {name: i for i, name in enumerate(catalog.UNITS, start=1)}
UNIT_NAMES = {uid: name for name, uid in UNIT_IDS.items()}
OPP_BY_KEY = {o["key"]: o for o in catalog.OPPORTUNITIES}
OPP_ID = {o["key"]: i for i, o in enumerate(catalog.OPPORTUNITIES, start=1)}
KEY_BY_ID = {v: k for k, v in OPP_ID.items()}


def essential_units(key: str) -> list[int]:
    return [UNIT_IDS[c] for c, imp, _ in OPP_BY_KEY[key]["requirements"] if imp == "essential"]


def make_student(rng: random.Random, strong_in: list[str]) -> dict[int, int]:
    strong = {u for key in strong_in for u in essential_units(key)}
    return {uid: rng.randint(*HIGH) if uid in strong else rng.randint(*LOW)
            for uid in UNIT_IDS.values()}


def build_students() -> list[dict]:
    rng = random.Random(SEED)
    students = []
    for opp in catalog.OPPORTUNITIES:
        for n in range(1, PER_OPPORTUNITY + 1):
            students.append({"id": f"S-{opp['key']}-{n}", "group": "standard",
                             "expected": [opp["key"]], "marks": make_student(rng, [opp["key"]])})
    for n, pair in enumerate(BORDERLINE_PAIRS, start=1):
        students.append({"id": f"B-{'+'.join(pair)}", "group": "borderline",
                         "expected": list(pair), "marks": make_student(rng, list(pair))})
    return students


def evaluate():
    model = build_model([{
        "id": OPP_ID[o["key"]],
        "title": o["title"],
        "requirements": [{"unit_id": UNIT_IDS[c], "importance": imp, "min_mark": mm}
                         for c, imp, mm in o["requirements"]],
    } for o in catalog.OPPORTUNITIES])

    rows = []
    for s in build_students():
        ranked = recommend(s["marks"], model)
        predicted = [KEY_BY_ID[r["opportunity_id"]] for r in ranked]
        rows.append({
            "student": s["id"],
            "group": s["group"],
            "expected": "+".join(s["expected"]),
            **{f"rank{i}": predicted[i - 1] for i in (1, 2, 3)},
            **{f"score{i}": ranked[i - 1]["match_score"] for i in (1, 2, 3)},
            "rank1_eligible": ranked[0]["meets_requirements"],
            "top1_hit": predicted[0] in s["expected"],
            "top3_hit": any(k in predicted[:3] for k in s["expected"]),
            # Borderline only: were BOTH strong domains ranked in the top 2?
            "both_in_top2": (set(s["expected"]) <= set(predicted[:2])
                             if s["group"] == "borderline" else ""),
            **{f"mark: {name}": s["marks"][uid] for name, uid in UNIT_IDS.items()},
        })
    return model, rows


def accuracy(rows, key):
    return sum(r[key] for r in rows) / len(rows) if rows else 0.0


def main():
    model, rows = evaluate()
    standard = [r for r in rows if r["group"] == "standard"]
    borderline = [r for r in rows if r["group"] == "borderline"]

    # ---- per-student table ----
    print(f"\n{'Student':<14}{'Expected':<11}{'Predicted #1':<14}{'Score':>7}  {'#2':<6}{'#3':<6}Result")
    print("-" * 66)
    for r in rows:
        print(f"{r['student']:<14}{r['expected']:<11}{r['rank1']:<14}{r['score1']:>7.4f}  "
              f"{r['rank2']:<6}{r['rank3']:<6}{'HIT' if r['top1_hit'] else 'MISS'}")

    # ---- summary ----
    summary = [
        ("Standard (n=%d)" % len(standard), accuracy(standard, "top1_hit"), accuracy(standard, "top3_hit")),
        ("Borderline (n=%d)" % len(borderline), accuracy(borderline, "top1_hit"), accuracy(borderline, "top3_hit")),
        ("All (n=%d)" % len(rows), accuracy(rows, "top1_hit"), accuracy(rows, "top3_hit")),
    ]
    print(f"\n{'Group':<22}{'Top-1':>10}{'Top-3':>10}")
    print("-" * 42)
    for name, t1, t3 in summary:
        print(f"{name:<22}{t1:>10.1%}{t3:>10.1%}")
    both = sum(r["both_in_top2"] for r in borderline)
    print(f"Borderline students with both domains in the top 2: {both}/{len(borderline)}")

    # ---- IDF weights for all 12 catalogue units ----
    # df = how many opportunities require the unit. A unit no opportunity requires isn't
    # in the model vocabulary, so it has no IDF weight (shown as "-").
    idf_by_unit = dict(zip(model["vocabulary"], model["idf"]))
    df = {uid: sum(UNIT_NAMES[uid] in {n for n, _, _ in o["requirements"]}
                   for o in catalog.OPPORTUNITIES) for uid in UNIT_IDS.values()}
    idf_rows = sorted(UNIT_IDS.values(), key=lambda u: (-idf_by_unit.get(u, 0), UNIT_NAMES[u]))
    print(f"\n{'Unit':<34}{'Required by':>12}{'IDF':>10}")
    print("-" * 56)
    for uid in idf_rows:
        w = f"{idf_by_unit[uid]:.4f}" if uid in idf_by_unit else "-"
        print(f"{UNIT_NAMES[uid]:<34}{df[uid]:>12}{w:>10}")

    # ---- CSV ----
    with open(RESULTS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        out = csv.writer(f)
        out.writerow([])
        out.writerow(["SUMMARY", "top1_accuracy", "top3_accuracy"])
        for name, t1, t3 in summary:
            out.writerow([name, f"{t1:.4f}", f"{t3:.4f}"])
        out.writerow(["borderline_both_in_top2", f"{both}/{len(borderline)}"])
        out.writerow([])
        out.writerow(["IDF", "unit_name", "required_by", "idf"])
        for uid in idf_rows:
            out.writerow(["", UNIT_NAMES[uid], df[uid],
                          f"{idf_by_unit[uid]:.6f}" if uid in idf_by_unit else ""])
        out.writerow([])
        out.writerow(["config", f"seed={SEED}", f"high={HIGH}", f"low={LOW}",
                      f"fitted_at={model['fitted_at']}"])
    print(f"\nSaved {RESULTS_PATH}")


if __name__ == "__main__":
    main()
