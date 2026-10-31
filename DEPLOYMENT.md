# Deploy the Workbase portfolio demo

This configuration publishes **one Docker-based service** on Render. It serves both the built React frontend and the FastAPI backend from the same origin. A Neon PostgreSQL database stores the sample records. Open registration is disabled and visitors enter through a **read-only demo**; the application cannot create, edit or delete any sample client, project or ticket through the demo account.

## 1. Database (Neon)

Create a free PostgreSQL database at https://console.neon.tech and copy its connection URL from Neon's dashboard. Use a connection string with SSL enabled (Neon supplies this). The URL looks like `postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require`. Do **not** commit or paste a real URL into a public file or chat.

Neon's free plan and Render's free service have usage and sleep limits; review their current pricing before confirming any provision.

## 2. Create the Render web service

Go to https://dashboard.render.com/select-repo?type=blueprint and connect your GitHub repository `damndwit/workbase-platform`, using the **Blueprint** flow if available. The repository root contains `render.yaml`. Confirm the service is **Free** before proceeding. Render may ask for payment details, and this setup cannot guarantee there will never be charges if you change plans.

Render's deployment settings are defined in `render.yaml`: its Docker build compiles the React frontend using Node.js and bundles it with a Python FastAPI runtime. No Node.js installation on the Render Python host is needed. When prompted for `DATABASE_URL`, paste the private PostgreSQL connection URL **only in Render's environment-variable field**. Render generates a random `WORKBASE_SECRET_KEY`; never share this secret.

No public credentials need to be created. On initial startup, Workbase creates a fictional read-only demo workspace and data automatically. Refreshes and restarts use the existing database records; do not delete the Neon database after launch.

## 3. Test before sharing

Open the Render-generated `.onrender.com` URL and verify:
- Page displays a **Explore read-only demo** button.
- Clicking it opens a workspace with fictional clients, projects and tickets.
- Viewing the dashboard and filtering records works.
- The interface does **not** offer mutation controls for the demo viewer.
- Direct API attempts to create/update/delete with the demo token return HTTP 403. The backend, not just the UI, enforces this.
- `/api/health` returns a working status and `/docs` displays the API documentation.
- Redeploying does not erase the seeded data.

## Important limitations

This is a **portfolio demo**, not a secure multi-tenant commercial SaaS service. It has not undergone an external security audit, lacks account recovery, rate limiting, production-grade cookie sessions, and migration tracking. Hosted registration is disabled and only synthetic information should be used. Never use real clients' or employees' data, and do not enable unrestricted registrations or real business use without additional hardening.

Render free services can sleep after inactivity and may take time to wake. Neon free storage is limited. A free `.onrender.com` URL is included; a personally owned `.com` domain still generally requires paying a registrar. If you already own a domain, connecting it may not incur extra hosting fees.

## Local development

Codespaces continues to use the existing SQLite database and normal registration/login without the production flags:

```bash
cd /workspaces/workbase-platform
bash scripts/dev.sh
```

**Never set `ENVIRONMENT=production` in your local Codespace unless you intentionally configured PostgreSQL and production secrets.**
