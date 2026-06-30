"""
Tests for backend/app/common/security.py
Verifies that the `cors_origins` field has been removed from the Settings model/schema.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_settings_class():
    """Import and return the Settings class (or equivalent) from security.py."""
    try:
        from backend.app.common.security import Settings
        return Settings
    except ImportError:
        pass

    try:
        from app.common.security import Settings
        return Settings
    except ImportError:
        pass

    pytest.skip("Cannot import Settings from security.py – adjust the import path.")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def Settings():
    return _get_settings_class()


@pytest.fixture()
def default_settings(Settings):
    """Return a default-constructed Settings instance (no arguments)."""
    try:
        return Settings()
    except Exception as exc:
        pytest.skip(f"Settings() could not be constructed with defaults: {exc}")


# ---------------------------------------------------------------------------
# 1. The `cors_origins` field must NOT exist on the Settings class/schema
# ---------------------------------------------------------------------------

class TestCorsOriginsFieldRemoved:

    def test_cors_origins_not_in_class_fields(self, Settings):
        """cors_origins should not be declared as a class attribute / model field."""
        # Pydantic v1
        if hasattr(Settings, "__fields__"):
            assert "cors_origins" not in Settings.__fields__, (
                "cors_origins is still declared in Settings.__fields__"
            )

        # Pydantic v2
        if hasattr(Settings, "model_fields"):
            assert "cors_origins" not in Settings.model_fields, (
                "cors_origins is still declared in Settings.model_fields"
            )

        # Dataclass / plain class
        import dataclasses
        if dataclasses.is_dataclass(Settings):
            field_names = {f.name for f in dataclasses.fields(Settings)}
            assert "cors_origins" not in field_names, (
                "cors_origins is still declared as a dataclass field"
            )

    def test_cors_origins_not_in_schema(self, Settings):
        """cors_origins must not appear in the JSON schema produced by Settings."""
        # Pydantic v1
        if hasattr(Settings, "schema"):
            schema = Settings.schema()
            props = schema.get("properties", {})
            assert "cors_origins" not in props, (
                "cors_origins is still present in Settings JSON schema properties"
            )

        # Pydantic v2
        if hasattr(Settings, "model_json_schema"):
            schema = Settings.model_json_schema()
            props = schema.get("properties", {})
            assert "cors_origins" not in props, (
                "cors_origins is still present in Settings model_json_schema properties"
            )

    def test_cors_origins_not_in_instance_dict(self, default_settings):
        """A freshly-constructed Settings instance must not carry a cors_origins attribute."""
        instance_dict = (
            default_settings.dict()
            if hasattr(default_settings, "dict")
            else (
                default_settings.model_dump()
                if hasattr(default_settings, "model_dump")
                else vars(default_settings)
            )
        )
        assert "cors_origins" not in instance_dict, (
            "cors_origins still appears in the serialised Settings dict"
        )

    def test_cors_origins_attribute_missing_on_instance(self, default_settings):
        """Accessing cors_origins on a Settings instance should raise AttributeError."""
        assert not hasattr(default_settings, "cors_origins"), (
            "Settings instance still exposes cors_origins as an attribute"
        )


# ---------------------------------------------------------------------------
# 2. Passing cors_origins must raise a validation / type error
# ---------------------------------------------------------------------------

class TestCorsOriginsRaisesOnConstruction:

    def _try_construct(self, Settings, value):
        """Attempt to construct Settings(cors_origins=value)."""
        try:
            instance = Settings(cors_origins=value)
            return instance, None
        except Exception as exc:
            return None, exc

    @pytest.mark.parametrize("value", [
        "http://localhost:5173",
        "http://example.com",
        None,
        ["http://localhost:5173"],
        "",
    ])
    def test_cors_origins_kwarg_raises(self, Settings, value):
        """
        Providing cors_origins=<any value> should either raise an error or
        silently ignore the unknown field – but must NOT store it.
        The field must not be accessible after construction.
        """
        instance, exc = self._try_construct(Settings, value)

        if exc is not None:
            # Any of these exception types are acceptable
            assert isinstance(exc, (
                TypeError,
                ValueError,
                # Pydantic ValidationError
                *_pydantic_validation_errors(),
            )), (
                f"Unexpected exception type {type(exc)} when passing cors_origins={value!r}: {exc}"
            )
        else:
            # Some frameworks silently ignore extra fields – verify it wasn't stored
            assert not hasattr(instance, "cors_origins"), (
                f"cors_origins={value!r} was accepted and stored on Settings instance"
            )
            instance_dict = _serialize(instance)
            assert "cors_origins" not in instance_dict, (
                f"cors_origins={value!r} appears in the serialised output"
            )

    def test_cors_origins_default_not_localhost(self, Settings):
        """
        The old default was 'http://localhost:5173'.
        After removal the field must not exist, so no default should be present.
        """
        # Pydantic v1
        if hasattr(Settings, "__fields__"):
            field = Settings.__fields__.get("cors_origins")
            assert field is None, (
                "cors_origins field still has a default of 'http://localhost:5173' in __fields__"
            )

        # Pydantic v2
        if hasattr(Settings, "model_fields"):
            field = Settings.model_fields.get("cors_origins")
            assert field is None, (
                "cors_origins field still has a default of 'http://localhost:5173' in model_fields"
            )


# ---------------------------------------------------------------------------
# 3. Serialisation / deserialisation round-trip does NOT include cors_origins
# ---------------------------------------------------------------------------

class TestSerialisation:

    def test_dict_serialisation_no_cors_origins(self, default_settings):
        """dict() / model_dump() must not include cors_origins."""
        data = _serialize(default_settings)
        assert "cors_origins" not in data

    def test_json_serialisation_no_cors_origins(self, default_settings):
        """JSON serialisation must not include cors_origins."""
        import json

        if hasattr(default_settings, "model_dump_json"):
            raw = default_settings.model_dump_json()
        elif hasattr(default_settings, "json"):
            raw = default_settings.json()
        else:
            raw = json.dumps(_serialize(default_settings))

        parsed = json.loads(raw)
        assert "cors_origins" not in parsed, (
            "cors_origins appears in JSON-serialised Settings"
        )

    def test_parse_payload_with_cors_origins_raises_or_ignores(self, Settings):
        """
        Parsing a raw dict that contains cors_origins must either raise
        or silently ignore the field – it must not be stored.
        """
        payload = {"cors_origins": "http://localhost:5173"}

        # Pydantic v2
        if hasattr(Settings, "model_validate"):
            try:
                instance = Settings.model_validate(payload)
                assert not hasattr(instance, "cors_origins")
                assert "cors_origins" not in _serialize(instance)
            except Exception as exc:
                assert isinstance(exc, (TypeError, ValueError, *_pydantic_validation_errors()))

        # Pydantic v1
        elif hasattr(Settings, "parse_obj"):
            try:
                instance = Settings.parse_obj(payload)
                assert not hasattr(instance, "cors_origins")
                assert "cors_origins" not in _serialize(instance)
            except Exception as exc:
                assert isinstance(exc, (TypeError, ValueError, *_pydantic_validation_errors()))

        else:
            # Generic constructor
            try:
                instance = Settings(**payload)
                assert not hasattr(instance, "cors_origins")
            except Exception as exc:
                assert isinstance(exc, (TypeError, ValueError, *_pydantic_validation_errors()))


# ---------------------------------------------------------------------------
# 4. Backward-incompatible usage explicitly verified
# ---------------------------------------------------------------------------

class TestBackwardIncompatibility:

    def test_old_default_value_not_present(self, Settings):
        """
        The old default 'http://localhost:5173' must not appear anywhere
        in the serialised output of a default Settings instance.
        """
        try:
            instance = Settings()
        except Exception:
            pytest.skip("Cannot construct Settings with defaults")

        data = _serialize(instance)
        for v in data.values():
            assert v != "http://localhost:5173", (
                "Old cors_origins default 'http://localhost:5173' still present in Settings"
            )

    def test_cors_origins_not_nullable_default(self, Settings):
        """
        The old field was non-nullable (nullable=False).
        After removal there should be no nullable=False cors_origins definition.
        """
        # Pydantic v1
        if hasattr(Settings, "__fields__"):
            field = Settings.__fields__.get("cors_origins")
            assert field is None, "cors_origins still defined with nullable=False"

        # Pydantic v2
        if hasattr(Settings, "model_fields"):
            field = Settings.model_fields.get("cors_origins")
            assert field is None, "cors_origins still defined in model_fields"

    def test_settings_construction_without_cors_origins_succeeds(self, Settings):
        """
        Settings should construct successfully without cors_origins.
        This is the primary forward-compatible usage.
        """
        try:
            instance = Settings()
            assert instance is not None
        except Exception as exc:
            pytest.fail(
                f"Settings() raised an unexpected error after cors_origins removal: {exc}"
            )


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _pydantic_validation_errors():
    """Return a tuple of known Pydantic ValidationError classes (if available)."""
    errors = []
    try:
        from pydantic import ValidationError
        errors.append(ValidationError)
    except ImportError:
        pass
    return tuple(errors)


def _serialize(instance):
    """Return a dict representation of a settings instance."""
    if hasattr(instance, "model_dump"):
        return instance.model_dump()
    if hasattr(instance, "dict"):
        return instance.dict()
    return vars(instance)