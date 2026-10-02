"""
Atomic conversion logic shared between fiat and crypto wallets.

Key correctness properties:
- Both the debit and the credit happen inside ONE database transaction.
  If anything fails after the debit but before the credit, the whole
  transaction rolls back — the user never loses funds into the void.
- Wallet rows are locked with SELECT ... FOR UPDATE before being read,
  so two concurrent conversions against the same wallet can't both read
  a stale balance and both succeed when only one should (a classic
  race condition in balance-mutation code).
- Insufficient balance raises before any write happens.
"""

import uuid
from decimal import ROUND_DOWN, Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import CRYPTO_LIST, FIAT_LIST
from app.core.exchange_rates import get_conversion_rate
from app.models.crypto_wallet import CryptoWallet
from app.models.wallet import FiatWallet

_FIAT_SET = set(FIAT_LIST)
_CRYPTO_SET = set(CRYPTO_LIST)


def _wallet_model_for(asset: str):
    if asset in _FIAT_SET:
        return FiatWallet, "currency"
    if asset in _CRYPTO_SET:
        return CryptoWallet, "coin"
    raise ValueError(f"Unsupported asset: {asset}")


def _decimals_for(asset: str) -> int:
    return 2 if asset in _FIAT_SET else 8


def _lock_wallet(db: Session, user_id: uuid.UUID, asset: str):
    """Row-lock a single wallet for update within the current transaction."""
    model, column_name = _wallet_model_for(asset)
    column = getattr(model, column_name)
    wallet = (
        db.query(model)
        .filter(model.user_id == user_id, column == asset)
        .with_for_update()
        .one_or_none()
    )
    if wallet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet for {asset} not found. It should have been auto-provisioned on first access.",
        )
    return wallet


def convert_between_wallets(
    db: Session,
    user_id: uuid.UUID,
    from_asset: str,
    to_asset: str,
    amount: Decimal,
) -> dict:
    """
    Atomically debit `amount` of from_asset and credit the equivalent
    amount of to_asset for the given user. Runs inside a single DB
    transaction; raises HTTPException (which triggers a rollback via
    the get_db dependency's session lifecycle) on any failure.

    Lock ordering: wallets are locked in a fixed order (alphabetical by
    asset code) rather than "from then to", so two concurrent opposite
    conversions (A->B and B->A) can't deadlock each other by acquiring
    locks in reverse order.
    """
    first_asset, second_asset = sorted([from_asset, to_asset])
    first_wallet = _lock_wallet(db, user_id, first_asset)
    second_wallet = _lock_wallet(db, user_id, second_asset)

    from_wallet = first_wallet if first_asset == from_asset else second_wallet
    to_wallet = first_wallet if first_asset == to_asset else second_wallet

    if from_wallet.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient {from_asset} balance. Available: {from_wallet.balance}, requested: {amount}",
        )

    rate = get_conversion_rate(from_asset, to_asset)
    credit_decimals = _decimals_for(to_asset)
    credited_amount = (amount * rate).quantize(Decimal(1).scaleb(-credit_decimals), rounding=ROUND_DOWN)

    # Two writes, one transaction. Nothing commits until both succeed.
    from_wallet.balance -= amount
    to_wallet.balance += credited_amount

    db.commit()
    db.refresh(from_wallet)
    db.refresh(to_wallet)

    return {
        "from_asset": from_asset,
        "to_asset": to_asset,
        "amount_debited": amount,
        "amount_credited": credited_amount,
        "rate_used": rate,
        "from_asset_new_balance": from_wallet.balance,
        "to_asset_new_balance": to_wallet.balance,
    }