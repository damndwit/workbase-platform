"""Optional invitation notifications over HTTPS. The site still works without email."""
import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)


# Email's optional; the in-app invite works either way.
def send_team_invitation(address: str, workspace: str, inviter: str, role: str) -> str:
    # Email is optional. Never block an invite just because the sender isn't set up.
    api_key = os.getenv("BREVO_API_KEY", "").strip()
    sender = os.getenv("WORKBASE_SENDER_EMAIL", "").strip()
    if not api_key or not sender:
        return "not_configured"

    site = (os.getenv("WORKBASE_PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL") or "https://workbase-demo.onrender.com").rstrip("/")
    message = (
        f"{inviter} invited you to join {workspace} on Workbase as a {role}.\n\n"
        f"Open {site}, sign in using your existing account, then open Team "
        "to accept the invitation.\n\n"
        "If you weren't expecting this, you can ignore the message."
    )
# Brevo uses this JSON format.
    payload = {
        "sender": {"name": "Workbase", "email": sender},
        "to": [{"email": address}],
        "subject": f"Invitation to {workspace} on Workbase",
        "textContent": message,
    }
# HTTP API instead of SMTP on free hosting.
    request = Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={"api-key": api_key, "content-type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=8) as response:
            return "submitted" if 200 <= response.status < 300 else "failed"
    except (HTTPError, URLError, TimeoutError, OSError):
        log.warning("Invitation email submission failed; invitation remains available in Workbase.")
        return "failed"
