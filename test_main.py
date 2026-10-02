"""
test_main.py

Full end-to-end tests for the currency platform API.

Run with:
    pytest test_main.py -v

Assumes a running/reachable PostgreSQL instance configured via the
same environment variables app/core/config.py reads (or a .env file).
This suite does not mock the DB — it exercises the real signup/login/
wallet/exchange flow against it, then cleans up.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.base_registry import Base
from app.db.session import engine
from app.main import app

API_PREFIX = "/api/v1"

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once for the test session."""
    Base.metadata.create_all(bind=engine)
    yield


def _unique_email() -> str:
    return f"test_{uuid.uuid4().hex[:10]}@example.com"


def _valid_password() -> str:
    return "StrongPass1!"


def _signup_and_login(email: str | None = None, password: str | None = None) -> str:
    email = email or _unique_email()
    password = password or _valid_password()

    signup_resp = client.post(
        f"{API_PREFIX}/auth/signup",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert signup_resp.status_code == 201, signup_resp.text

    login_resp = client.post(
        f"{API_PREFIX}/auth/login",
        data={"username": email, "password": password},
    )
    assert login_resp.status_code == 200, login_resp.text
    return login_resp.json()["access_token"]


class TestSignup:
    def test_signup_success(self):
        payload = {
            "email": _unique_email(),
            "password": _valid_password(),
            "full_name": "Jane Doe",
            "preferred_fiat_currency": "USD",
            "preferred_crypto_currency": "BTC",
        }
        resp = client.post(f"{API_PREFIX}/auth/signup", json=payload)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["email"] == payload["email"]
        assert body["is_active"] is True
        assert "hashed_password" not in body
        assert "password" not in body

    def test_signup_duplicate_email_returns_409(self):
        email = _unique_email()
        payload = {"email": email, "password": _valid_password()}
        first = client.post(f"{API_PREFIX}/auth/signup", json=payload)
        assert first.status_code == 201, first.text

        second = client.post(f"{API_PREFIX}/auth/signup", json=payload)
        assert second.status_code == 409

    def test_signup_invalid_email_returns_422(self):
        payload = {"email": "not-an-email", "password": _valid_password()}
        resp = client.post(f"{API_PREFIX}/auth/signup", json=payload)
        assert resp.status_code == 422

    def test_signup_weak_password_missing_special_char_returns_422(self):
        payload = {"email": _unique_email(), "password": "NoSpecial1"}
        resp = client.post(f"{API_PREFIX}/auth/signup", json=payload)
        assert resp.status_code == 422

    def test_signup_weak_password_too_short_returns_422(self):
        payload = {"email": _unique_email(), "password": "Sh0rt!"}
        resp = client.post(f"{API_PREFIX}/auth/signup", json=payload)
        assert resp.status_code == 422

    def test_signup_invalid_preferred_fiat_currency_returns_422(self):
        payload = {
            "email": _unique_email(),
            "password": _valid_password(),
            "preferred_fiat_currency": "XYZ",
        }
        resp = client.post(f"{API_PREFIX}/auth/signup", json=payload)
        assert resp.status_code == 422

    def test_signup_invalid_preferred_crypto_currency_returns_422(self):
        payload = {
            "email": _unique_email(),
            "password": _valid_password(),
            "preferred_crypto_currency": "NOTACOIN",
        }
        resp = client.post(f"{API_PREFIX}/auth/signup", json=payload)
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self):
        email = _unique_email()
        password = _valid_password()
        client.post(f"{API_PREFIX}/auth/signup", json={"email": email, "password": password})

        resp = client.post(
            f"{API_PREFIX}/auth/login",
            data={"username": email, "password": password},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self):
        email = _unique_email()
        password = _valid_password()
        client.post(f"{API_PREFIX}/auth/signup", json={"email": email, "password": password})

        resp = client.post(
            f"{API_PREFIX}/auth/login",
            data={"username": email, "password": "WrongPass1!"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user_returns_401(self):
        resp = client.post(
            f"{API_PREFIX}/auth/login",
            data={"username": _unique_email(), "password": _valid_password()},
        )
        assert resp.status_code == 401

    def test_login_missing_fields_returns_422(self):
        resp = client.post(f"{API_PREFIX}/auth/login", data={"username": "only@example.com"})
        assert resp.status_code == 422


class TestMe:
    def test_me_with_valid_token(self):
        email = _unique_email()
        token = _signup_and_login(email=email)
        resp = client.get(f"{API_PREFIX}/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["email"] == email

    def test_me_without_token_returns_401(self):
        resp = client.get(f"{API_PREFIX}/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token_returns_401(self):
        resp = client.get(
            f"{API_PREFIX}/auth/me",
            headers={"Authorization": "Bearer not.a.valid.token"},
        )
        assert resp.status_code == 401


class TestFiatWallet:
    def test_get_fiat_wallet_success(self):
        token = _signup_and_login()
        resp = client.get(f"{API_PREFIX}/wallets/fiat", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        expected_currencies = {"USD", "EUR", "GBP", "BDT", "INR", "AED", "CAD", "AUD"}
        assert set(body["balances"].keys()) == expected_currencies
        for balance in body["balances"].values():
            assert balance == "0.00"

    def test_get_fiat_wallet_without_token_returns_401(self):
        resp = client.get(f"{API_PREFIX}/wallets/fiat")
        assert resp.status_code == 401


class TestCryptoWallet:
    def test_get_crypto_wallet_success(self):
        token = _signup_and_login()
        resp = client.get(f"{API_PREFIX}/wallets/crypto", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        expected_coins = {"BTC", "ETH", "USDT", "BNB", "SOL", "ADA", "XRP", "DOT", "DOGE", "MATIC"}
        assert set(body["balances"].keys()) == expected_coins
        for balance in body["balances"].values():
            assert balance == "0.00000000"

    def test_get_crypto_wallet_without_token_returns_401(self):
        resp = client.get(f"{API_PREFIX}/wallets/crypto")
        assert resp.status_code == 401


class TestExchangeConvert:
    def test_convert_insufficient_balance_returns_400(self):
        token = _signup_and_login()
        resp = client.post(
            f"{API_PREFIX}/exchange/convert",
            json={"from_asset": "USD", "to_asset": "BDT", "amount": "100"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "Insufficient" in resp.json()["detail"]

    def test_convert_same_asset_returns_422(self):
        token = _signup_and_login()
        resp = client.post(
            f"{API_PREFIX}/exchange/convert",
            json={"from_asset": "USD", "to_asset": "USD", "amount": "10"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_convert_unsupported_asset_returns_422(self):
        token = _signup_and_login()
        resp = client.post(
            f"{API_PREFIX}/exchange/convert",
            json={"from_asset": "USD", "to_asset": "NOTACOIN", "amount": "10"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_convert_negative_amount_returns_422(self):
        token = _signup_and_login()
        resp = client.post(
            f"{API_PREFIX}/exchange/convert",
            json={"from_asset": "USD", "to_asset": "BDT", "amount": "-5"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_convert_zero_amount_returns_422(self):
        token = _signup_and_login()
        resp = client.post(
            f"{API_PREFIX}/exchange/convert",
            json={"from_asset": "USD", "to_asset": "BDT", "amount": "0"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_convert_without_token_returns_401(self):
        resp = client.post(
            f"{API_PREFIX}/exchange/convert",
            json={"from_asset": "USD", "to_asset": "BDT", "amount": "10"},
        )
        assert resp.status_code == 401


class TestHealthAndCurrencies:
    def test_root_health_check(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_list_currencies(self):
        resp = client.get(f"{API_PREFIX}/currencies")
        assert resp.status_code == 200
        body = resp.json()
        assert body["fiat"] == ["USD", "EUR", "GBP", "BDT", "INR", "AED", "CAD", "AUD"]
        assert body["crypto"] == [
            "BTC", "ETH", "USDT", "BNB", "SOL", "ADA", "XRP", "DOT", "DOGE", "MATIC",
        ]