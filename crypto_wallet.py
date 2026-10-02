"""
CRUD / provisioning logic for CryptoWallet. Same pattern as
app/crud/wallet.py (fiat) — kept as a separate module rather than
generalized, since fiat and crypto are likely to diverge (crypto will
need on-chain address linkage, network/chain fields, etc. later).
"""

import uuid
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import CRYPTO_LIST
from app.models.crypto_wallet import CryptoWallet

_COIN_ORDER = {code: index for index, code in enumerate(CRYPTO_LIST)}


def get_or_create_crypto_wallets(db: Session, user_id: uuid.UUID) -> list[CryptoWallet]:
    """
    Ensure the user has exactly one wallet row per coin in CRYPTO_LIST,
    creating any missing ones with a 0 balance, then return all 10 rows
    in CRYPTO_LIST order. Race-safe against concurrent first-access
    provisioning, same as the fiat equivalent.
    """
    wallets = db.query(CryptoWallet).filter(CryptoWallet.user_id == user_id).all()
    existing_coins = {w.coin for w in wallets}
    missing = [code for code in CRYPTO_LIST if code not in existing_coins]

    if missing:
        for code in missing:
            db.add(CryptoWallet(user_id=user_id, coin=code, balance=Decimal("0.00000000")))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        wallets = db.query(CryptoWallet).filter(CryptoWallet.user_id == user_id).all()

    return sorted(wallets, key=lambda w: _COIN_ORDER[w.coin])