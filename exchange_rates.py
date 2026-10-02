"""
MOCKED exchange rates for local testing only.

All rates are expressed as "1 unit of this asset = X USD". Every
conversion is computed via USD as a common base (asset_A -> USD ->
asset_B) rather than needing a full N x N rate matrix. This is a
placeholder — replace with a live rate provider (and add staleness
checks / spread / fees) before this ever touches real money.
"""

from decimal import Decimal

# Fiat: units of that currency per 1 USD (e.g. 1 USD = 120 BDT)
_FIAT_PER_USD: dict[str, Decimal] = {
    "USD": Decimal("1"),
    "EUR": Decimal("0.92"),
    "GBP": Decimal("0.79"),
    "BDT": Decimal("120"),
    "INR": Decimal("83.5"),
    "AED": Decimal("3.67"),
    "CAD": Decimal("1.36"),
    "AUD": Decimal("1.52"),
}

# Crypto: USD value of 1 unit of that coin (e.g. 1 BTC = 60,000 USD)
_CRYPTO_USD_VALUE: dict[str, Decimal] = {
    "BTC": Decimal("60000"),
    "ETH": Decimal("3000"),
    "USDT": Decimal("1"),
    "BNB": Decimal("550"),
    "SOL": Decimal("140"),
    "ADA": Decimal("0.45"),
    "XRP": Decimal("0.55"),
    "DOT": Decimal("6.5"),
    "DOGE": Decimal("0.12"),
    "MATIC": Decimal("0.70"),
}


def usd_value_of(asset: str, amount: Decimal) -> Decimal:
    """Convert an amount of any supported fiat or crypto asset into USD."""
    if asset in _FIAT_PER_USD:
        return amount / _FIAT_PER_USD[asset]
    if asset in _CRYPTO_USD_VALUE:
        return amount * _CRYPTO_USD_VALUE[asset]
    raise ValueError(f"Unsupported asset: {asset}")


def amount_from_usd(asset: str, usd_amount: Decimal) -> Decimal:
    """Convert a USD amount into an amount of the target fiat or crypto asset."""
    if asset in _FIAT_PER_USD:
        return usd_amount * _FIAT_PER_USD[asset]
    if asset in _CRYPTO_USD_VALUE:
        return usd_amount / _CRYPTO_USD_VALUE[asset]
    raise ValueError(f"Unsupported asset: {asset}")


def get_conversion_rate(from_asset: str, to_asset: str) -> Decimal:
    """Direct from_asset -> to_asset rate, i.e. how much to_asset you get per 1 from_asset."""
    usd = usd_value_of(from_asset, Decimal("1"))
    return amount_from_usd(to_asset, usd)