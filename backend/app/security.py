"""Development authentication. Do not expose without production security hardening."""
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlmodel import Session, select

from .database import get_session
from .models import User, Workspace

# An ephemeral secret is safe for local demos but logins expire after a restart.
# Configure a stable high-entropy secret before any controlled deployment.
SECRET = os.getenv("WORKBASE_SECRET_KEY") or secrets.token_urlsafe(48)
ISSUER = "workbase-local"
ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)

def token_for_user(user: User) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": str(user.id), "iss": ISSUER,
        "iat": now, "exp": now + timedelta(hours=12),
    }, SECRET, algorithm=ALGORITHM)

def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None:
        raise HTTPException(401, "Please sign in", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET,
            algorithms=[ALGORITHM], issuer=ISSUER,
            options={"require": ["sub", "iat", "exp", "iss"]},
        )
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(401, "Invalid or expired session", headers={"WWW-Authenticate": "Bearer"}) from exc
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(401, "Account no longer exists")
    return user

def owned_workspace(user: User, session: Session) -> Workspace:
    workspace = session.exec(select(Workspace).where(Workspace.owner_id == user.id)).first()
    if workspace is None:
        raise HTTPException(403, "No workspace available")
    return workspace
