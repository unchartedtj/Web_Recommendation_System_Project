# WBL Placement Recommendation System

A data-driven recommendation system for **Work-Based Learning (WBL) placement** at Strathmore University.

- **Students** enter their marks, skills and career interests, and get internships ranked by how well they match.
- **Industry partners** post internships, review candidates, and accept them.
- **The WBL office (system admin)** manages placement records, users, the catalogue and the model, and reads the usability (SUS) results.

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Flask (REST API), SQLAlchemy, Flask-Migrate, Flask-JWT-Extended, scikit-learn |
| Frontend | React 18 + Vite 6, react-router, axios, recharts |
| Database | MySQL / MariaDB (XAMPP) |
| Recommendation engine | TF-IDF + cosine similarity: **60% grades, 25% skills, 15% interests**, plus minimum-mark eligibility rules |

```
backend/    Flask API: app/ (routes, models, services), migrations/, services/recommendation_engine.py,
            evaluation/ (offline accuracy + ablation study), tests/
frontend/   React app: src/pages, src/components, src/api, src/__tests__
```

---

## 1. Setup (first time)

**You need:** Python 3.10+, Node.js 20+, and XAMPP (MySQL/MariaDB).

1. **Start MySQL** in the XAMPP Control Panel, then create the two databases once:
   ```powershell
   & "<xampp folder>\mysql\bin\mysql.exe" -u root -e "CREATE DATABASE IF NOT EXISTS wbl_placement CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE DATABASE IF NOT EXISTS wbl_placement_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
   ```
2. **Set up the backend:**
   ```powershell
   cd backend
   python -m venv venv
   .\venv\Scripts\pip.exe install -r requirements.txt
   Copy-Item .env.example .env        # then edit: DB password, JWT_SECRET_KEY, optionally DEFAULT_ADMIN_PASSWORD
   .\venv\Scripts\flask.exe db upgrade
   .\venv\Scripts\flask.exe seed-data # demo data; prints the admin password ONCE if it creates the admin
   ```
3. **Set up the frontend:**
   ```powershell
   cd frontend
   npm.cmd install
   ```

### Running it
- **Easiest:** open the project folder in **VS Code**. The tasks in `.vscode/tasks.json` start MySQL (if needed), the backend and the frontend automatically. The first time, allow automatic tasks when VS Code asks.
- **By hand**, in two terminals:
  ```powershell
  cd backend;  .\venv\Scripts\flask.exe run      # http://localhost:5000
  cd frontend; npm.cmd run dev                   # http://localhost:5173
  ```
- Then open **http://localhost:5173**.

### A clean demo database
```powershell
cd backend
.\venv\Scripts\flask.exe reset-demo
```
- **What it does:** deletes **all** data, re-runs the migrations, loads the demo data and retrains the model.
- **Confirmation:** you must type `RESET` (or pass `--confirm RESET`). It refuses to run when `FLASK_ENV=production`.
- **Admin password:** it prints a new admin password, unless you set `DEFAULT_ADMIN_PASSWORD` in `backend/.env` to a password with 8+ characters including a letter and a number.

---

## 2. Demo accounts

Students and partners all use the password **`DemoPass123`**.

| Log in with | Role | What it demonstrates |
|---|---|---|
| `samuel.kamau@strathmore.edu` | Student | A strong Software Development profile: **Software Development Intern is #1**. Has a pending application. |
| `diana.wanjiru@strathmore.edu` | Student | A Data profile. Data Analytics is #1; Software Development is under **"Below minimum"** (OOP 52 < 60). One application is shortlisted and one is pending (below minimum, acknowledged). |
| `kevin.mwangi@strathmore.edu` | Student | **No profile yet**: shows the empty states and "Complete your profile to apply". |
| `info@techcorp.co.ke` | Industry partner | Owns Software Development, Web & Mobile, and Data Analytics. Reviews candidates and accepts them (which creates placements). |
| `info@netsecure.co.ke` | Industry partner | Owns Networking & IT Support and IT Business / Systems Analyst. |
| **`Admin`** (username) | System admin | The full admin dashboard. The password is printed by `flask seed-data` / `flask reset-demo` when the admin is created. |

---

## 3. 10-minute demo script

| Time | As | Do this | Point out |
|---|---|---|---|
| 0:00 | `info@techcorp.co.ke` | **Post Opportunity**: title, sector, units (with essential/desirable and minimum marks), skills, slots, deadline → Save | The model retrains automatically |
| 1:30 | `kevin.mwangi@…` | **Dashboard** shows an incomplete profile → **My Profile**: enter all 12 marks, pick skills and 1–3 interests → Save | The validation messages |
| 3:00 | `kevin.mwangi@…` | **Recommendations**: ranked cards with match %, **"Why this match?"**, and the eligible vs "Below minimum" sections | TF-IDF + cosine, 60/25/15 |
| 4:00 | `kevin.mwangi@…` | Open the top internship → **Apply** → add a note → Confirm → **My Applications** | The snapshot of the match is frozen at apply time |
| 5:00 | `info@techcorp.co.ke` | **My Opportunities → View candidates**: sorted by match → **Details** (units, skills, note) → **Shortlist** (the email appears) → **Accept** with start and end dates | Slots filled x/y; the student's other applications are withdrawn automatically |
| 6:30 | `kevin.mwangi@…` | **Dashboard**: "Your placement" card; **My Applications** shows the placement panel | |
| 7:00 | `Admin` | **Placements** (TC09): the new record → **Edit** → status **Ongoing** with a start date → Save | Allowed transitions only; Terminated needs a reason |
| 8:00 | `Admin` | **Overview** charts, **Users** (deactivate impact preview), **Activity Log** | Every action is logged |
| 9:00 | `Admin` | **SUS Results** (TC10): mean vs 68 → **Model**: retrain, IDF weights, ablation table (98% → 100% top-1) | |

---

## 4. Tests

```powershell
cd backend;  .\venv\Scripts\python.exe -m pytest     # uses the separate wbl_placement_test database
cd frontend; npm.cmd test
cd backend;  .\venv\Scripts\python.exe -m evaluation.evaluate_engine   # offline accuracy + ablation
```

---

## 5. API overview

All errors look like `{"error": "...", "fields": {...}}`.

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/change-password` |
| Student | `GET/PUT /api/student/profile`, `GET /api/recommendations`, `GET /api/opportunities[/<id>]`, `POST /api/applications`, `GET /api/applications/mine`, `PATCH /api/applications/<id>/withdraw` |
| Partner | `/api/partner/opportunities[...]`, `GET /api/partner/opportunities/<id>/candidates`, `PATCH /api/partner/applications/<id>` |
| Feedback | `GET /api/sus/questions`, `GET /api/sus/mine`, `PUT /api/sus` |
| Admin | `/api/admin/overview`, `placements` (+ `export.csv`), `students`, `partners`, `opportunities`, `users`, `admins`, `skills`, `sectors`, `units`, `model`, `model/retrain`, `sus` (+ `export.csv`), `activity` |

**Security:**
- **Passwords:** hashed with scrypt.
- **Login:** JWT tokens, with role checks on every endpoint.
- **Deactivated accounts:** can't log in, and their existing tokens are rejected.
- **Admin password resets:** force a password change at the next login.

**Note on units:** `flask seed-data` keeps the academic units in line with its 12-unit catalogue. A unit an admin added that nobody has used yet is removed by the next re-seed; a unit that's in use is only deactivated.
