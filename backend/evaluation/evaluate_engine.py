"""Offline evaluation of the recommendation engine, with an ABLATION study (for Chapter 5).

Run from the backend folder:
    python -m evaluation.evaluate_engine

The script builds labelled synthetic students (grades + skills + career interests) and
checks whether the engine recommends the internship each student was designed for. It
uses the seeded demo opportunities (app/seed/catalog.py) and the pure engine functions,
so it needs NO database.

Student groups (fixed random seed, so results are reproducible):
- aligned (30, 6 per internship): grades, skills and interest all point to one internship.
    grades: 75-95 in the target's ESSENTIAL units, 40-70 in every other unit
    skills: the target's essential skills + 0-1 of its desirable skills
    interests: the target's sector + 0-1 random other sector
- borderline (10, 2 per pair): strong grades, essential skills and interests in TWO
  internships. Either one counts as correct.
- noisy (10, 2 per internship): like aligned, but every mark gets random ±15 noise
  (kept within 0-100) and 1-2 random extra skills are added.
- conflicting (10): grades point to internship A, the interest points to internship B,
  and the skills are neutral (from neither A nor B). We report which side wins.

Ablation (which inputs matter?) — the same students are scored with three weightings:
    grades only        1.00 / 0.00 / 0.00
    grades + skills    0.70 / 0.30 / 0.00
    all three          0.60 / 0.25 / 0.15   (the system's configuration)

Metrics: Top-1 accuracy (expected internship ranked #1) and Top-3 accuracy (in the top 3).
Outputs: a printed report, evaluation/results.csv (per student) and evaluation/ablation.csv.
"""
import csv
import os
import random

from app.seed import catalog
from services.recommendation_engine import build_model, recommend

# A fixed random seed: the "random" data comes out the same on every run,
# so your Chapter 5 numbers are reproducible.
SEED = 42
HIGH, LOW = (75, 95), (40, 70)          # mark ranges for strong units / everything else
NOISE = 15                              # ± noise added to every mark in the noisy group
OUT_DIR = os.path.dirname(__file__)

CONFIGS = [                             # (name, weights)
    ("grades_only", {"grades": 1.00, "skills": 0.00, "interests": 0.00}),
    ("grades_skills", {"grades": 0.70, "skills": 0.30, "interests": 0.00}),
    ("all_three", {"grades": 0.60, "skills": 0.25, "interests": 0.15}),
]
BORDERLINE_PAIRS = [("SWE", "WEB"), ("WEB", "DATA"), ("DATA", "BA"), ("NET", "SWE"), ("BA", "SWE")]
# (grades point to A, interest points to B) — every internship appears on both sides.
CONFLICT_PAIRS = [("SWE", "DATA"), ("WEB", "BA"), ("DATA", "NET"), ("NET", "WEB"), ("BA", "SWE"),
                  ("SWE", "NET"), ("WEB", "DATA"), ("DATA", "BA"), ("NET", "SWE"), ("BA", "WEB")]

# Plain-data ids: units, skills, sectors and opportunities are numbered in catalogue order.
UNIT_IDS = {name: i for i, name in enumerate(catalog.UNITS, start=1)}           # name → id
UNIT_NAMES = {uid: name for name, uid in UNIT_IDS.items()}                       # id → name
SKILL_IDS = {name: i for i, (name, _) in enumerate(catalog.SKILLS, start=1)}
SKILL_NAMES = {sid: name for name, sid in SKILL_IDS.items()}
SECTOR_IDS = {name: i for i, name in enumerate(catalog.SECTORS, start=1)}
SECTOR_NAMES = {sid: name for name, sid in SECTOR_IDS.items()}
OPP_BY_KEY = {o["key"]: o for o in catalog.OPPORTUNITIES}                        # "SWE" → details
OPP_ID = {o["key"]: i for i, o in enumerate(catalog.OPPORTUNITIES, start=1)}     # "SWE" → 1
KEY_BY_ID = {v: k for k, v in OPP_ID.items()}                                    # 1 → "SWE"
KEYS = list(OPP_ID)


# =============================================================================
# Building the synthetic students
# =============================================================================

def essential_units(key):
    return [UNIT_IDS[n] for n, imp, _ in OPP_BY_KEY[key]["requirements"] if imp == "essential"]


def skills_of(key, importance):
    return [SKILL_IDS[n] for n, imp in OPP_BY_KEY[key]["skills"] if imp == importance]


def sector_of(key):
    return SECTOR_IDS[OPP_BY_KEY[key]["sector"]]


def make_marks(rng, strong_in):
    """HIGH marks in the essential units of the given internships, LOW everywhere else."""
    strong = {u for key in strong_in for u in essential_units(key)}
    return {uid: rng.randint(*HIGH) if uid in strong else rng.randint(*LOW)
            for uid in UNIT_IDS.values()}


def aligned_student(rng, key):
    """Grades, skills and interest all point to `key`."""
    skills = skills_of(key, "essential") + rng.sample(skills_of(key, "desirable"),
                                                      rng.randint(0, 1))
    others = [s for s in SECTOR_IDS.values() if s != sector_of(key)]
    interests = [sector_of(key)] + rng.sample(others, rng.randint(0, 1))
    return make_marks(rng, [key]), skills, interests


def build_students():
    rng = random.Random(SEED)
    students = []

    for key in KEYS:                                      # aligned: 6 per internship
        for n in range(1, 7):
            marks, skills, interests = aligned_student(rng, key)
            students.append({"id": f"A-{key}-{n}", "group": "aligned", "expected": [key],
                             "marks": marks, "skills": skills, "interests": interests})

    for a, b in BORDERLINE_PAIRS:                         # borderline: 2 per pair
        for n in range(1, 3):
            skills = sorted(set(skills_of(a, "essential") + skills_of(b, "essential")))
            students.append({"id": f"B-{a}+{b}-{n}", "group": "borderline", "expected": [a, b],
                             "marks": make_marks(rng, [a, b]), "skills": skills,
                             "interests": [sector_of(a), sector_of(b)]})

    for key in KEYS:                                      # noisy: 2 per internship
        for n in range(1, 3):
            marks, skills, interests = aligned_student(rng, key)
            marks = {u: max(0, min(100, m + rng.randint(-NOISE, NOISE))) for u, m in marks.items()}
            extra = [s for s in SKILL_IDS.values() if s not in skills]
            skills = skills + rng.sample(extra, rng.randint(1, 2))
            students.append({"id": f"N-{key}-{n}", "group": "noisy", "expected": [key],
                             "marks": marks, "skills": skills, "interests": interests})

    for a, b in CONFLICT_PAIRS:                           # conflicting: grades → a, interest → b
        used = set(skills_of(a, "essential") + skills_of(a, "desirable")
                   + skills_of(b, "essential") + skills_of(b, "desirable"))
        neutral = [s for s in SKILL_IDS.values() if s not in used]
        students.append({"id": f"C-{a}vs{b}", "group": "conflicting", "expected": [a],
                         "grade_side": a, "interest_side": b,
                         "marks": make_marks(rng, [a]), "skills": rng.sample(neutral, 2),
                         "interests": [sector_of(b)]})
    return students


# =============================================================================
# Running the engine
# =============================================================================

def build_catalog_model():
    return build_model([{
        "id": OPP_ID[o["key"]],
        "title": o["title"],
        "sector_id": SECTOR_IDS[o["sector"]],
        "requirements": [{"unit_id": UNIT_IDS[n], "importance": imp, "min_mark": mm}
                         for n, imp, mm in o["requirements"]],
        "skills": [{"skill_id": SKILL_IDS[n], "importance": imp} for n, imp in o["skills"]],
    } for o in catalog.OPPORTUNITIES])


def evaluate():
    """Rank every student under every configuration. Returns (model, students, results)
    where results[config][student_id] = predicted keys in rank order."""
    model = build_catalog_model()
    students = build_students()
    results = {name: {} for name, _ in CONFIGS}
    for name, weights in CONFIGS:
        for s in students:
            ranked = recommend(s["marks"], model, skill_ids=s["skills"],
                               sector_ids=s["interests"], weights=weights)
            results[name][s["id"]] = [KEY_BY_ID[r["opportunity_id"]] for r in ranked]
    return model, students, results


def summarise(students, results):
    """One row per configuration × group with Top-1/Top-3 (and winners for 'conflicting')."""
    rows = []
    groups = ["aligned", "borderline", "noisy"]
    for name, _ in CONFIGS:
        for group in groups + ["all_labelled"]:
            members = [s for s in students if (s["group"] in groups if group == "all_labelled"
                                               else s["group"] == group)]
            top1 = sum(results[name][s["id"]][0] in s["expected"] for s in members)
            top3 = sum(any(k in results[name][s["id"]][:3] for k in s["expected"]) for s in members)
            rows.append({"config": name, "group": group, "n": len(members),
                         "top1": round(top1 / len(members), 4), "top3": round(top3 / len(members), 4),
                         "grade_side_wins": "", "interest_side_wins": "", "other_wins": ""})
        conflicting = [s for s in students if s["group"] == "conflicting"]
        firsts = [results[name][s["id"]][0] for s in conflicting]
        grade_wins = sum(f == s["grade_side"] for f, s in zip(firsts, conflicting))
        interest_wins = sum(f == s["interest_side"] for f, s in zip(firsts, conflicting))
        rows.append({"config": name, "group": "conflicting", "n": len(conflicting),
                     "top1": "", "top3": "", "grade_side_wins": grade_wins,
                     "interest_side_wins": interest_wins,
                     "other_wins": len(conflicting) - grade_wins - interest_wins})
    return rows


# =============================================================================
# Report
# =============================================================================

def main():
    model, students, results = evaluate()
    summary = summarise(students, results)

    # ---- per-student table (system configuration: all three) ----
    print(f"\n{'Student':<18}{'Group':<12}{'Expected':<11}"
          + "".join(f"{name:<15}" for name, _ in CONFIGS))
    print("-" * (41 + 15 * len(CONFIGS)))
    for s in students:
        expected = (f"{s['grade_side']}|{s['interest_side']}" if s["group"] == "conflicting"
                    else "+".join(s["expected"]))
        cells = []
        for name, _ in CONFIGS:
            top = results[name][s["id"]][0]
            mark = ("G" if top == s["grade_side"] else "I" if top == s["interest_side"] else "-") \
                if s["group"] == "conflicting" else ("HIT" if top in s["expected"] else "MISS")
            cells.append(f"{top} {mark}".ljust(15))
        print(f"{s['id']:<18}{s['group']:<12}{expected:<11}" + "".join(cells))
    print("(conflicting: G = grades side won, I = interest side won)")

    # ---- ablation table ----
    print(f"\n{'Configuration':<16}{'Group':<15}{'n':>4}{'Top-1':>9}{'Top-3':>9}"
          f"{'Grade wins':>12}{'Interest wins':>15}")
    print("-" * 80)
    for r in summary:
        t1 = f"{r['top1']:.1%}" if r["top1"] != "" else ""
        t3 = f"{r['top3']:.1%}" if r["top3"] != "" else ""
        print(f"{r['config']:<16}{r['group']:<15}{r['n']:>4}{t1:>9}{t3:>9}"
              f"{str(r['grade_side_wins']):>12}{str(r['interest_side_wins']):>15}")

    # ---- IDF weights ----
    def df(item_id, key, id_map):
        return sum(item_id in {id_map[x[0]] for x in o[key]} for o in catalog.OPPORTUNITIES)

    unit_idf = dict(zip(model["vocabulary"], model["idf"]))
    skill_idf = dict(zip(model["skill_vocabulary"], model["skill_idf"]))
    print(f"\n{'Unit':<34}{'Required by':>12}{'IDF':>10}")
    print("-" * 56)
    for uid in sorted(UNIT_IDS.values(), key=lambda u: (-unit_idf.get(u, 0), UNIT_NAMES[u])):
        w = f"{unit_idf[uid]:.4f}" if uid in unit_idf else "-"
        print(f"{UNIT_NAMES[uid]:<34}{df(uid, 'requirements', UNIT_IDS):>12}{w:>10}")
    print(f"\n{'Skill':<34}{'Required by':>12}{'IDF':>10}")
    print("-" * 56)
    for sid in sorted(SKILL_IDS.values(), key=lambda s: (-skill_idf.get(s, 0), SKILL_NAMES[s])):
        w = f"{skill_idf[sid]:.4f}" if sid in skill_idf else "- (not required)"
        print(f"{SKILL_NAMES[sid]:<34}{df(sid, 'skills', SKILL_IDS):>12}{w:>10}")

    # ---- CSV files ----
    with open(os.path.join(OUT_DIR, "ablation.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    with open(os.path.join(OUT_DIR, "results.csv"), "w", newline="", encoding="utf-8") as f:
        fieldnames = (["student", "group", "expected", "grade_side", "interest_side", "skills",
                       "interests"]
                      + [f"{name}_{c}" for name, _ in CONFIGS for c in ("rank1", "rank2", "rank3",
                                                                        "top1_hit", "top3_hit")]
                      + [f"mark: {n}" for n in UNIT_IDS])
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in students:
            row = {"student": s["id"], "group": s["group"], "expected": "+".join(s["expected"]),
                   "grade_side": s.get("grade_side", ""), "interest_side": s.get("interest_side", ""),
                   "skills": "; ".join(SKILL_NAMES[x] for x in s["skills"]),
                   "interests": "; ".join(SECTOR_NAMES[x] for x in s["interests"])}
            for name, _ in CONFIGS:
                ranked = results[name][s["id"]]
                row.update({f"{name}_rank1": ranked[0], f"{name}_rank2": ranked[1],
                            f"{name}_rank3": ranked[2],
                            f"{name}_top1_hit": ranked[0] in s["expected"],
                            f"{name}_top3_hit": any(k in ranked[:3] for k in s["expected"])})
            row.update({f"mark: {n}": s["marks"][uid] for n, uid in UNIT_IDS.items()})
            writer.writerow(row)
    print(f"\nSaved {os.path.join(OUT_DIR, 'results.csv')}")
    print(f"Saved {os.path.join(OUT_DIR, 'ablation.csv')}")


if __name__ == "__main__":
    main()
