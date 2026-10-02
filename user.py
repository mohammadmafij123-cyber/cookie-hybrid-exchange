"""
CRUD operations for the User model. Kept free of HTTP concerns so it
can be reused by other endpoints, background jobs, or scripts.
"""

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user_in: UserCreate) -> User:
    """Create a new user with a securely hashed password.

    Assumes the caller has already checked for an existing email
    (see the /auth/signup endpoint) to return a clean 409 rather
    than relying solely on the DB unique-constraint error.
    """
    db_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        preferred_fiat_currency=user_in.preferred_fiat_currency,
        preferred_crypto_currency=user_in.preferred_crypto_currency,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
from app.core.security import verify_password


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Return the User if email exists and password matches, else None.
    Deliberately returns None (not distinct errors) for both 'no such
    user' and 'wrong password' so the login endpoint can give a single
    generic error — this prevents user-enumeration via error messages."""
    user = get_user_by_email(db, email=email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user