"""Auth dependencies: resolve current user from JWT, and role guards."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .auth import decode_access_token
from .database import get_db
from .models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise cred_exc
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise cred_exc
    return user


def require_roles(*roles: str):
    """Guard factory: allow only listed roles (Admin always allowed)."""
    def guard(user: User = Depends(get_current_user)) -> User:
        if user.role != "Admin" and user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return guard
