# Backend setup

Run these commands from `sih_backend`. Python 3.12 is recommended.

1. Create a virtual environment: `python -m venv .venv`.
   Activate it with `.venv\Scripts\Activate.ps1` in Windows PowerShell,
   or `source .venv/bin/activate` on macOS/Linux.
2. Install dependencies: `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` (`Copy-Item .env.example .env` in PowerShell,
   or `cp .env.example .env` on macOS/Linux). Replace the placeholders with
   your PostgreSQL connection details. Alternatively, set `DATABASE_URL`
   directly in your shell environment; it takes precedence over `.env`.
   Percent-encode reserved characters in the URL username/password.
4. Install/start PostgreSQL and create the target database using pgAdmin or
   `createdb -h localhost -U username database_name` with your actual values.
   The configured database user must be able to connect and create tables.
5. Start the server: `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`.
6. Backend: http://127.0.0.1:8000 — API docs: http://127.0.0.1:8000/docs.

The backend loads `.env` from `sih_backend` regardless of the working directory.
Never commit `.env`; the example contains placeholders only.

Missing `DATABASE_URL` stops configuration with an explicit error. Importing
`app.main` with a configured URL does not connect to PostgreSQL. Server startup
creates missing tables using the existing models; PostgreSQL must be reachable
and the database must already exist. A connection/initialization failure stops
startup with a configuration-oriented error rather than starting an unusable API.

`create_all()` does not update existing tables or migrate old schemas. Existing
database schema updates remain a separate task; do not drop existing data as a
setup step. The optional existing demo seed command is `python -m app.seed_cases`;
it uses the same configuration and requires a reachable database.
