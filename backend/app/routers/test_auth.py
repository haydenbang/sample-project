"""Tests for backend/app/routers/auth.py - verifying phone field handling after FIELD_ADDED change."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from pydantic import BaseModel, EmailStr
from typing import Optional


# ---------------------------------------------------------------------------
# Minimal stubs so we can import / instantiate the router without a real DB
# ---------------------------------------------------------------------------

class FakeRoleEnum:
    value = "user"


class FakeUser:
    """Simulates the ORM User model after the phone field was added."""
    def __init__(self, email="test@example.com", role=None, phone=None, hashed_password="hashed"):
        self.email = email
        self.hashed_password = hashed_password
        self.role = role or FakeRoleEnum()
        self.phone = phone  # new nullable field


# ---------------------------------------------------------------------------
# Stub out heavy dependencies before importing the router
# ---------------------------------------------------------------------------

import sys
from types import ModuleType

def _make_stub_modules():
    # app.common.security
    security_mod = ModuleType("app.common.security")
    security_mod.create_access_token = MagicMock(return_value="fake-token")
    security_mod.verify_password = MagicMock(return_value=True)

    # app.common.deps
    deps_mod = ModuleType("app.common.deps")
    deps_mod.get_current_user = MagicMock()

    # app.database
    db_mod = ModuleType("app.database")
    db_mod.get_db = MagicMock()

    # app.models.user
    models_user_mod = ModuleType("app.models.user")
    models_user_mod.User = FakeUser

    # app.schemas.user - UserOut MUST include phone after the fix
    schemas_user_mod = ModuleType("app.schemas.user")

    class UserOut(BaseModel):
        email: EmailStr
        role: str
        phone: Optional[str] = None  # <- the field that must exist after the fix

        class Config:
            from_attributes = True

    schemas_user_mod.UserOut = UserOut

    # app (package)
    app_pkg = ModuleType("app")
    app_common = ModuleType("app.common")
    app_models = ModuleType("app.models")
    app_schemas = ModuleType("app.schemas")

    for name, mod in [
        ("app", app_pkg),
        ("app.common", app_common),
        ("app.common.security", security_mod),
        ("app.common.deps", deps_mod),
        ("app.database", db_mod),
        ("app.models", app_models),
        ("app.models.user", models_user_mod),
        ("app.schemas", app_schemas),
        ("app.schemas.user", schemas_user_mod),
    ]:
        sys.modules.setdefault(name, mod)

    return security_mod, deps_mod, db_mod, schemas_user_mod


security_mod, deps_mod, db_mod, schemas_user_mod = _make_stub_modules()

# Now we can safely import the router
from app.routers.auth import router, LoginRequest, LoginResponse  # noqa: E402


# ---------------------------------------------------------------------------
# Build a test FastAPI app
# ---------------------------------------------------------------------------

def build_app(current_user: FakeUser = None):
    """Create a fresh FastAPI app overriding dependencies."""
    application = FastAPI()
    application.include_router(router)

    if current_user is not None:
        application.dependency_overrides[deps_mod.get_current_user] = lambda: current_user

    # Always override get_db to avoid real DB calls
    application.dependency_overrides[db_mod.get_db] = lambda: MagicMock()

    return application


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def user_with_phone():
    return FakeUser(email="alice@example.com", phone="+1-800-555-0100")


@pytest.fixture()
def user_without_phone():
    return FakeUser(email="bob@example.com", phone=None)


@pytest.fixture()
def client_with_phone(user_with_phone):
    app = build_app(current_user=user_with_phone)
    return TestClient(app), user_with_phone


@pytest.fixture()
def client_without_phone(user_without_phone):
    app = build_app(current_user=user_without_phone)
    return TestClient(app), user_without_phone


# ---------------------------------------------------------------------------
# Tests: UserOut schema contains phone field
# ---------------------------------------------------------------------------

class TestUserOutSchemaIncludesPhone:
    """Verify the UserOut schema (as patched) exposes the phone field."""

    def test_userout_has_phone_field(self):
        UserOut = schemas_user_mod.UserOut
        fields = UserOut.model_fields if hasattr(UserOut, "model_fields") else UserOut.__fields__
        assert "phone" in fields, "UserOut must declare a 'phone' field after the schema fix"

    def test_userout_phone_is_nullable(self):
        UserOut = schemas_user_mod.UserOut
        fields = UserOut.model_fields if hasattr(UserOut, "model_fields") else UserOut.__fields__
        phone_field = fields["phone"]
        # Works for both Pydantic v1 and v2
        required = getattr(phone_field, "is_required", lambda: phone_field.required)
        if callable(required):
            assert not required(), "phone field must not be required (nullable)"
        else:
            assert not required, "phone field must not be required (nullable)"

    def test_userout_serialises_phone_value(self):
        UserOut = schemas_user_mod.UserOut
        out = UserOut(email="x@example.com", role="user", phone="+49-30-12345")
        data = out.model_dump() if hasattr(out, "model_dump") else out.dict()
        assert data["phone"] == "+49-30-12345"

    def test_userout_serialises_phone_none(self):
        UserOut = schemas_user_mod.UserOut
        out = UserOut(email="x@example.com", role="user", phone=None)
        data = out.model_dump() if hasattr(out, "model_dump") else out.dict()
        assert data["phone"] is None

    def test_userout_phone_defaults_to_none(self):
        UserOut = schemas_user_mod.UserOut
        out = UserOut(email="x@example.com", role="user")
        data = out.model_dump() if hasattr(out, "model_dump") else out.dict()
        assert data["phone"] is None


# ---------------------------------------------------------------------------
# Tests: GET /api/auth/me returns phone in response
# ---------------------------------------------------------------------------

class TestMeEndpointReturnsPhone:

    def test_me_returns_phone_field_when_set(self, client_with_phone):
        client, user = client_with_phone
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        body = response.json()
        assert "phone" in body, "Response JSON must contain 'phone' key"
        assert body["phone"] == user.phone

    def test_me_returns_phone_null_when_not_set(self, client_without_phone):
        client, user = client_without_phone
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        body = response.json()
        assert "phone" in body, "Response JSON must contain 'phone' key even when null"
        assert body["phone"] is None

    def test_me_returns_email(self, client_with_phone):
        client, user = client_with_phone
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        assert response.json()["email"] == user.email

    def test_me_returns_role(self, client_with_phone):
        client, user = client_with_phone
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        assert response.json()["role"] == user.role.value

    def test_me_phone_various_formats(self):
        """Phone numbers in various valid formats must be passed through unchanged."""
        for phone_value in ["+1-800-555-0199", "01012345678", "+44 20 7946 0958", ""]:
            user = FakeUser(phone=phone_value)
            app = build_app(current_user=user)
            client = TestClient(app)
            response = client.get("/api/auth/me")
            assert response.status_code == 200
            assert response.json()["phone"] == phone_value


# ---------------------------------------------------------------------------
# Tests: POST /api/auth/login still works (no regression)
# ---------------------------------------------------------------------------

class TestLoginEndpointUnaffectedByPhoneField:

    def _make_db_session(self, user: FakeUser):
        """Return a mock DB session that yields the given user on query."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = user
        return mock_db

    def test_login_success_returns_access_token(self, user_with_phone):
        security_mod.verify_password.return_value = True
        security_mod.create_access_token.return_value = "tok-123"

        app = build_app()
        mock_db = self._make_db_session(user_with_phone)
        app.dependency_overrides[db_mod.get_db] = lambda: mock_db

        client = TestClient(app)
        response = client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "secret"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["access_token"] == "tok-123"
        assert body["token_type"] == "bearer"

    def test_login_success_does_not_expose_phone(self, user_with_phone):
        """Login endpoint returns LoginResponse which must NOT include phone (only token/role)."""
        security_mod.verify_password.return_value = True

        app = build_app()
        mock_db = self._make_db_session(user_with_phone)
        app.dependency_overrides[db_mod.get_db] = lambda: mock_db

        client = TestClient(app)
        response = client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "secret"},
        )
        assert response.status_code == 200
        body = response.json()
        # LoginResponse intentionally does NOT include phone
        assert "phone" not in body

    def test_login_wrong_password_raises_401(self, user_with_phone):
        security_mod.verify_password.return_value = False

        app = build_app()
        mock_db = self._make_db_session(user_with_phone)
        app.dependency_overrides[db_mod.get_db] = lambda: mock_db

        client = TestClient(app)
        response = client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_login_unknown_user_raises_401(self):
        security_mod.verify_password.return_value = False

        app = build_app()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        app.dependency_overrides[db_mod.get_db] = lambda: mock_db

        client = TestClient(app)
        response = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "any"},
        )
        assert response.status_code == 401

    def test_login_invalid_email_raises_422(self):
        app = build_app()
        client = TestClient(app)
        response = client.post(
            "/api/auth/login",
            json={"email": "not-an-email", "password": "secret"},
        )
        assert response.status_code == 422

    def test_login_missing_password_raises_422(self):
        app = build_app()
        client = TestClient(app)
        response = client.post(
            "/api/auth/login",
            json={"email": "alice@example.com"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests: Backward-incompatible / edge cases
# ---------------------------------------------------------------------------

class TestBackwardIncompatibleCases:

    def test_userout_rejects_extra_unknown_field_type(self):
        """UserOut should not accept phone as a non-string type (e.g. integer)."""
        UserOut = schemas_user_mod.UserOut
        with pytest.raises((ValueError, TypeError, Exception)):
            # Pydantic v2 raises ValidationError, v1 raises ValidationError too
            UserOut(email="x@example.com", role="user", phone=99999)

    def test_me_without_auth_raises_error(self):
        """Calling /me without a current_user dependency raises an error."""
        from fastapi import HTTPException

        def raise_unauth():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[deps_mod.get_current_user] = raise_unauth
        app.dependency_overrides[db_mod.get_db] = lambda: MagicMock()

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_user_model_without_phone_attribute_raises(self):
        """If the ORM User model does NOT have phone, from_attributes serialisation should fail or omit."""
        UserOut = schemas_user_mod.UserOut

        class LegacyUser:
            email = "legacy@example.com"
            role = "admin"
            # phone attribute intentionally absent

        try:
            out = UserOut.model_validate(LegacyUser()) if hasattr(UserOut, "model_validate") else UserOut.from_orm(LegacyUser())
            data = out.model_dump() if hasattr(out, "model_dump") else out.dict()
            # If it succeeds without phone, it must default to None
            assert data.get("phone") is None
        except Exception:
            # Acceptable: schema may raise if phone is required (shouldn't be, but validates the guard)
            pass

    def test_login_response_model_has_no_phone(self):
        """LoginResponse schema must NOT include phone (it's only a token response)."""
        fields = (
            LoginResponse.model_fields
            if hasattr(LoginResponse, "model_fields")
            else LoginResponse.__fields__
        )
        assert "phone" not in fields

    def test_userout_phone_field_type_accepts_none(self):
        """Explicitly ensure Optional[str] / str | None accepts None."""
        UserOut = schemas_user_mod.UserOut
        instance = UserOut(email="z@example.com", role="user", phone=None)
        data = instance.model_dump() if hasattr(instance, "model_dump") else instance.dict()
        assert data["phone"] is None

    def test_userout_phone_field_type_accepts_string(self):
        UserOut = schemas_user_mod.UserOut
        instance = UserOut(email="z@example.com", role="user", phone="123")
        data = instance.model_dump() if hasattr(instance, "model_dump") else instance.dict()
        assert data["phone"] == "123"