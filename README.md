# Workbase

A small business management web app built with React, TypeScript, FastAPI and SQLModel.

Right now it supports client records, projects, status updates, and a dashboard with live counts. It's an early version, built independently rather than copying a SaaS template.

**Stack:** React, TypeScript, Vite, HTML/CSS, Python, FastAPI, SQLModel, SQLite (local default), PostgreSQL (configurable), pytest, GitHub Actions.

## Run in GitHub Codespaces

Create a Codespace for this repository. Open **two terminals** from the repository root.

**Terminal 1: Backend**
```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2: Frontend**
```bash
cd frontend
npm install
npm run dev
```

Open the forwarded **5173** port. The Vite development server forwards calls to `/api` to the backend on port 8000. API docs are at forwarded port 8000, `/docs`.

If port 5173 opens but the app shows an API error, check that terminal 1 is running. When developing in Codespaces, avoid exposing ports publicly.

## Test the application

1. Open Clients and add a fictional client with an example.com email.
2. Change the client from Lead to Active.
3. Open Projects, add a project for that client, and change its status to Done.
4. Return to Overview and check whether all four dashboard totals update.
5. Try to delete a client that still has a project; the API should block it with a conflict.
6. Delete the project and then the client.

Backend tests:
```bash
cd backend
python -m pytest -q
```

Frontend type check and build:
```bash
cd frontend
npm run build
```

GitHub Actions runs both checks after each push.

## API routes

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Check server health |
| GET, POST | `/api/clients` | List/add clients |
| PATCH, DELETE | `/api/clients/{id}` | Update/remove a client |
| GET, POST | `/api/projects` | List/add projects |
| PATCH, DELETE | `/api/projects/{id}` | Update/remove a project |
| GET | `/api/summary` | Dashboard counts |

## Database

The initial release uses SQLite for simple local setup. For PostgreSQL, install and configure a database and set `DATABASE_URL` to a valid PostgreSQL connection string (with the installed psycopg driver). SQLModel manages the initial local table creation.

## Current limitations

**Do not deploy this application publicly yet.** This first milestone intentionally has **no user authentication or tenant/workspace isolation**. Anyone able to access its API could modify all data. Use fictional demo data and local/Codespaces development only. Authentication, database migrations, organization-level authorization, more advanced SaaS features and production deployment will be implemented separately.

## Repository structure

- `frontend/src/App.tsx` — React dashboard, forms and API interactions
- `frontend/src/style.css` — custom responsive styling
- `frontend/vite.config.ts` — development API proxy
- `backend/app/main.py` — REST API routes
- `backend/app/models.py` — SQLModel database tables
- `backend/app/schemas.py` — typed validation contracts
- `backend/app/database.py` — database sessions and engine
- `backend/tests/test_api.py` — endpoint and CRUD tests

This repository contains original source code for the Workbase learning project.

**Status:** Initial files committed; review CI results and perform the browser acceptance checks before describing the release as fully tested.
