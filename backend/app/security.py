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
from .models import User, Workspace, WorkspaceMember

# An ephemeral secret is safe for local demos but logins expire after a restart.
# Configure a stable high-entropy secret before any controlled deployment.
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
PUBLIC_DEMO_MODE = os.getenv("PUBLIC_DEMO_MODE", "0") == "1"
DEMO_EMAIL = "demo@workbase.example"
supplied_secret = os.getenv("WORKBASE_SECRET_KEY", "")
if ENVIRONMENT == "production" and len(supplied_secret) < 32:
    raise RuntimeError("Set WORKBASE_SECRET_KEY to a random string at least 32 characters long.")
SECRET = supplied_secret or secrets.token_urlsafe(48)
ISSUER = "workbase"
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

def workspace_access(user: User, session: Session, workspace_id: int | None = None):
    own = owned_workspace(user, session)
    target_id = workspace_id if workspace_id is not None else own.id
    if (PUBLIC_DEMO_MODE or os.getenv("WORKBASE_GUEST_PREVIEW", "0") == "1") and user.email == DEMO_EMAIL:
        if target_id != own.id:
            raise HTTPException(403, "Demo access is restricted to its sample workspace")
        return own, "viewer"
    if target_id == own.id:
        return own, "owner"
    membership = session.exec(select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == target_id,
        WorkspaceMember.user_id == user.id,
        WorkspaceMember.accepted == True,
    )).first()
    if membership is None:
        raise HTTPException(403, "Workspace access denied")
    workspace = session.get(Workspace, target_id)
    if workspace is None:
        raise HTTPException(404, "Workspace not found")
    return workspace, membership.role

def require_role(role: str, allowed: tuple[str, ...]):
    if role not in allowed:
        raise HTTPException(403, "Insufficient workspace permissions")
