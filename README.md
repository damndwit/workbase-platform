# Workbase

A small business management web app built with React, TypeScript, FastAPI and SQLModel.

The current version supports user registration, login, personally owned and shared team workspaces, client records, projects, status updates and dashboard totals. It's an early version, built independently rather than copying a SaaS template.

**Stack:** React, TypeScript, Vite, HTML/CSS, Python, FastAPI, SQLModel, JWT, Argon2, SQLite (local default), PostgreSQL (configurable), pytest, GitHub Actions.

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

## Team roles

The first account to create a workspace is its **Owner**. Owners can invite existing registered users and manage clients and projects. **Editors** may add/update projects and clients but cannot delete clients or invite members. **Viewers** can only read. Invitations appear on the invited user's Team page and require explicit acceptance. This is an in-app demonstration; no invitation emails are sent. Users retain their own personal workspace when joining another workspace.

This release adds a new membership table to the existing local SQLite database using SQLModel table creation. It does not delete existing clients, projects or accounts. There is not yet a full migration or invitation expiration/revocation system.

## Test the application

1. Register a **demo account** with a fictional name and example.com email. Sign in if you already registered.
2. Create a second fictional account and check that its personal workspace starts empty.
3. In the first account, visit **Team**, invite the second account as Viewer or Editor, then sign in to the second account and accept the invitation.
4. Use the workspace selector to switch between the personal workspace and the shared workspace; confirm Editor can manage projects but Viewer cannot change anything.
3. Open Clients and add a fictional client with an example.com email.
4. Change the client from Lead to Active.
5. Open Projects, add a project for that client, and change its status to Done.
6. Return to Overview and check whether all four dashboard totals update.
7. Try to delete a client that still has a project; the API should block it with a conflict.
8. Delete the project and then the client.

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
| POST | `/api/auth/register` | Register account and workspace |
| POST | `/api/auth/login` | Log in and issue a bearer token |
| GET | `/api/auth/me` | Read current account |
| GET | `/api/workspaces` | List accessible workspaces |
| GET | `/api/invitations` | List pending team invitations |
| POST | `/api/invitations/{id}/accept` | Accept invitation |
| GET | `/api/workspaces/{id}/members` | View team members |
| POST | `/api/workspaces/{id}/invite` | Invite existing user (owner only) |
| GET, POST | `/api/clients` | List/add clients |
| PATCH, DELETE | `/api/clients/{id}` | Update/remove a client |
| GET, POST | `/api/projects` | List/add projects |
| PATCH, DELETE | `/api/projects/{id}` | Update/remove a project |
| GET | `/api/summary` | Dashboard counts |

## Database

Authentication uses a fresh local SQLite file `backend/workbase_v2.db` to keep the earlier unauthenticated demo records separate rather than attempting an unsafe schema migration. The old `workbase.db` is left untouched. SQLModel creates tables on startup for this development milestone; formal database migrations are still needed for production.

For PostgreSQL, install and configure a database and set `DATABASE_URL` to a valid PostgreSQL connection string (with the installed psycopg driver). SQLModel manages the initial local table creation.

## Current limitations

**Do not deploy this application publicly yet.** Registration, password hashing, signed bearer tokens, and workspace role checks are implemented for local testing, but this is **not a production security review**. No email verification, invitation notifications, membership removal, account recovery, rate limiting, robust session management or schema migrations exist yet. Only use fictional sample data. The default signing secret is ephemeral and changes when the backend restarts; this intentionally signs out existing sessions. For persistent local sessions, set `WORKBASE_SECRET_KEY` as a private environment variable; never commit it to GitHub. Token storage in browser sessionStorage is a developmental choice, not hardened production session design.

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

**Status:** Team membership and permissions code committed. Review the latest CI results and test invitations in two different demo accounts.
