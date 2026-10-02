"""
Imports every model so they register on Base.metadata.

Import THIS module (not app.db.base directly) anywhere you need
Base.metadata to be aware of all tables — e.g. Alembic env.py,
create_tables.py. This avoids the circular import that happens when
model modules need Base but base.py also needs the models.
"""
from app.db.base import Base  # noqa: F401

# জটলা কাটাতে প্রথমে ওয়ালেট মডেলগুলো লোড হবে, তারপর ইউজার মডেল
from app.models.wallet import FiatWallet  # noqa: F401
from app.models.crypto_wallet import CryptoWallet  # noqa: F401
from app.models.user import User  # noqa: F401
