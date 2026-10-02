"""
Shared FastAPI dependencies, imported by endpoint modules.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.crud.user import get_user_by_email
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import TokenPayload

# tokenUrl points at the login endpoint so /docs shows the "Authorize" flow correctly.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Decode and validate the bearer JWT, then load the corresponding user.

    Raises 401 for: missing/malformed token, invalid signature, expired
    token, or a token whose subject no longer maps to a user. All of
    these return the same generic error so callers can't distinguish
    "token is bad" from "user was deleted" — that distinction is not
    useful to an attacker and not necessary for legitimate clients.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
    except JWTError:
        raise credentials_exception

    token_data = TokenPayload(**payload)
    if token_data.sub is None:
        raise credentials_exception

    user = get_user_by_email(db, email=token_data.sub)
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Extra guard on top of get_current_user: rejects deactivated accounts
    even if their token is otherwise still valid."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user