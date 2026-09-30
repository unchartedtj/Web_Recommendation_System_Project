# WBL Placement Recommendation System

A Data-Driven Recommendation System for Work-Based Learning (WBL) Placement at Strathmore University.

| Layer    | Tech                                                                  |
|----------|-----------------------------------------------------------------------|
| Backend  | Python 3.12, Flask (app factory), Flask-SQLAlchemy, Flask-Migrate, Flask-JWT-Extended, Flask-CORS, PyMySQL |
| Frontend | React 18 + Vite 6, react-router-dom, axios                            |
| Database | MySQL / MariaDB (tested on XAMPP MariaDB 10.4)                        |

**Current scope:** database schema (all 12 ERD tables) and authentication (register, login, current user).

```
backend/    Flask REST API  (app/, migrations/, tests/)
frontend/   React SPA       (src/api, src/pages, src/components, src/context)
```

---

## Prerequisites (Windows)
- Python 3.10+ (`python --version`)
- Node.js 20+ (`node --version`)
- XAMPP (MySQL/MariaDB) or any MySQL 8 server

## 1. Start MySQL
Open the **XAMPP Control Panel** and click **Start** next to **MySQL**.
Or, from PowerShell (adjust the path to your XAMPP folder):
```powershell
& "C:\xampp\mysql_start.bat"
```

Create the app database and the test database (run once):
```powershell
& "C:\xampp\mysql\bin\mysql.exe" -u root -e "CREATE DATABASE IF NOT EXISTS wbl_placement CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE DATABASE IF NOT EXISTS wbl_placement_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

## 2. Backend setup (first time)
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
Copy-Item .env.example .env          # then edit .env (DB password, JWT_SECRET_KEY)
flask db upgrade                     # creates all tables
```

## 3. Run the backend
```powershell
cd backend
.\venv\Scripts\Activate.ps1
flask run                            # http://localhost:5000  (health check: /api/health)
```

## 4. Create a system admin
Admins cannot self-register through the API. Create one from the CLI:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
flask create-admin                   # prompts for email, name, password
```

## 5. Frontend setup and run
```powershell
cd frontend
npm install                          # first time only
npm run dev                          # http://localhost:5173
```
The API URL defaults to `http://localhost:5000/api`. To change it, copy `frontend/.env.example` to `frontend/.env`.

## 6. Run the tests
Tests use the separate `wbl_placement_test` database (created automatically if missing, and wiped between tests).
```powershell
cd backend
.\venv\Scripts\Activate.ps1
pytest -v
```

---

## API summary
All errors use the shape `{"error": "message", "fields": {"field_name": "message"}}`.

| Method | Endpoint             | Auth   | Notes |
|--------|----------------------|--------|-------|
| POST   | `/api/auth/register` | –      | `role`: `student` or `industry_partner`. Returns 201, 400 (validation), or 409 (duplicate email/admission no). |
| POST   | `/api/auth/login`    | –      | Returns `access_token` (JWT claims include `user_id`, `role`) and `user`. Wrong credentials → 401. |
| GET    | `/api/auth/me`       | Bearer | Current user and profile. |

**Student fields:** `email, password, confirm_password, admission_no, first_name, last_name, course, year_of_study`
**Industry partner fields:** `email, password, confirm_password, organization_name, contact_person, phone`

## Schema changes
After editing a model in `backend/app/models/`:
```powershell
flask db migrate -m "describe the change"
flask db upgrade
```

## Troubleshooting
- **`Can't connect to MySQL server on 'localhost' (10061)`**: MySQL isn't running. Start it in XAMPP.
- **XAMPP MySQL stops immediately** with `Incorrect file format 'proxies_priv'` in `mysql\data\mysql_error.log`: the XAMPP system tables are corrupted. Back up `mysql\data`, then restore the `mysql` system folder from `mysql\backup`.
- **CORS errors in the browser**: make sure the frontend runs on port 5173, or update `FRONTEND_ORIGIN` in `backend/.env`.
