# Workbase

I wanted one place to deal with freelance website stuff, marketing clients, and support tickets. Keeping everything in random notes and chats was getting old, so I made Workbase.

It's a personal full-stack project. I started with a basic dashboard, got the frontend talking to a Python API, and kept adding things I would actually want in a client portal.

**[Live site](https://workbaseticket.onrender.com/)** · **[My GitHub](https://github.com/dwitdev)**

## What I worked on

1. Built the dashboard in **React, TypeScript, HTML, and CSS**. Went for a dark, clean look with a little retro feel.
2. Added a **FastAPI** backend with REST endpoints for clients, projects, tickets, and notes.
3. Connected **PostgreSQL** through **SQLModel**, so the records stick around instead of resetting every time.
4. Added logins, hashed passwords, **JWTs**, team workspaces, and role-based permissions.
5. Set up ticket statuses, priorities, a conversation history, and optional email invites.
6. Containerized the app using **Docker**, hosted it on **Render**, and added **GitHub Actions + pytest** checks.

## Stack

**Frontend:** JavaScript / TypeScript, React, HTML5, CSS3, Vite  
**Backend:** Python, FastAPI, Pydantic, REST APIs  
**Database:** PostgreSQL, SQL, SQLModel, Neon  
**Other:** Docker, Git, GitHub Actions, Render, JWT, Argon2, pytest

I built this to get better at frontend development, backend logic, databases, and how the pieces of a SaaS-style app fit together. I also wanted a project I could actually click around in, not just a screenshot.

Guest access uses sample data. My own workspace is separate. Still a personal learning project, so I wouldn't put sensitive client records in it without more security work.
