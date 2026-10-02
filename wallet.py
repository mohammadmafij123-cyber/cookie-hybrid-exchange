"""
CRUD / provisioning logic for FiatWallet.
"""

import uuid
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import FIAT_LIST
from app.models.wallet import FiatWallet

_CURRENCY_ORDER = {code: index for index, code in enumerate(FIAT_LIST)}


def get_or_create_fiat_wallets(db: Session, user_id: uuid.UUID) -> list[FiatWallet]:
    """
    Ensure the user has exactly one wallet row per currency in FIAT_LIST,
    creating any missing ones with a 0.00 balance, then return all 8
    rows in FIAT_LIST order.

    Handles the race where two concurrent first-time requests both try
    to create the same missing wallet: the UniqueConstraint on
    (user_id, currency) rejects the loser, which we catch and resolve
    by re-reading from the DB rather than raising a 500.
    """
    wallets = db.query(FiatWallet).filter(FiatWallet.user_id == user_id).all()
    existing_currencies = {w.currency for w in wallets}
    missing = [code for code in FIAT_LIST if code not in existing_currencies]

    if missing:
        for code in missing:
            db.add(FiatWallet(user_id=user_id, currency=code, balance=Decimal("0.00")))
        try:
            db.commit()
        except IntegrityError:
            # Another request created one of these concurrently — that's fine,
            # just discard our attempt and re-read the current state.
            db.rollback()
        wallets = db.query(FiatWallet).filter(FiatWallet.user_id == user_id).all()

    return sorted(wallets, key=lambda w: _CURRENCY_ORDER[w.currency])