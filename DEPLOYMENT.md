# Workbase public deployment

**Live demo:** https://workbase-demo.onrender.com/

Workbase runs on a single **Render Free Docker web service** connected to this repository. The Dockerfile builds React using Node.js, installs the FastAPI backend with Python, and serves the compiled UI and API from one origin.

## Current free launch configuration

- Render service: `workbase-demo` (Free plan, Virginia).
- Environment: `ENVIRONMENT=public_demo` and `PUBLIC_DEMO_MODE=1`.
- Database: local SQLite on Render's **ephemeral** container filesystem, seeded with **fictional** clients, projects and tickets at startup.
- Visitor access: **Explore read-only demo**; no password or new account required.
- Permissions: server-side workspace role checks restrict the public demo token to viewer access. Hosted account registration is disabled.
- Automatic deployments: connected to the repository's `main` branch.

**The database can reset when the service restarts or redeploys.** This is intentional for a read-only recruiter demo. It is not suitable for storing real user data or modifications. Use the Codespaces development environment for CRUD testing.

## Deploying the same free demo

1. Sign into [Render](https://dashboard.render.com/) and connect the GitHub repository `damndwit/workbase-platform`.
2. Create a **Web Service** using the repository's `Dockerfile` or choose the repository's `render.yaml` Blueprint.
3. Select the **Free** plan and Docker runtime. Set `ENVIRONMENT=public_demo` and `PUBLIC_DEMO_MODE=1`.
4. Publish the service and open its assigned `.onrender.com` URL.
5. Use **Explore read-only demo** and check the Overview, Clients, Projects, Tickets and Team pages.

Do not set `ENVIRONMENT=production` without a persistent PostgreSQL database and a strong `WORKBASE_SECRET_KEY`. The `production` option is a separate, more advanced configuration; it is **not required** for the existing free demonstration.

## Smoke tests

- `GET /api/health` returns HTTP 200 with `demo_available: true`.
- The live React dashboard loads sample clients, projects and tickets.
- Sign-in is available through the demo button, without public registration.
- Demo viewers cannot create, edit or delete records; the API also rejects these operations.
- The GitHub Actions workflow runs Python backend tests and a TypeScript/React build.

## Limits and future hosting

Render Free instances may sleep when inactive and take time to resume. Free-plan quotas and availability may change. The domain `workbase-demo.onrender.com` is included with hosting; an independently registered `.com` normally costs money.

To support permanent data and real user accounts in the future, use persistent PostgreSQL (such as Neon), formal schema migrations, production-managed signing keys, rate limiting, improved session handling, account recovery and a separate security review. **Do not store real customer information in this demo.**

## Local development

GitHub Codespaces keeps its existing independent SQLite database and normal registration and editing features:

```bash
cd /workspaces/workbase-platform
bash scripts/dev.sh
```
