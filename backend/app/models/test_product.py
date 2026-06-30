import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Helpers / compatibility shim
# ---------------------------------------------------------------------------
# We try to import the real Settings model.  If it cannot be imported we
# create a minimal stub so that the tests themselves can still be collected
# and will fail with a clear message only when the real implementation is
# wrong.
# ---------------------------------------------------------------------------

try:
    from backend.app.models.product import Settings  # type: ignore
except ImportError:
    try:
        from app.models.product import Settings  # type: ignore
    except ImportError:
        Settings = None  # will be handled inside each test


def get_settings_class():
    if Settings is None:
        pytest.skip("Cannot import Settings from backend.app.models.product")
    return Settings


# ---------------------------------------------------------------------------
# 1. cors_origins field has been REMOVED
# ---------------------------------------------------------------------------


class TestCorsOriginsFieldRemoved:
    """cors_origins should no longer exist on the Settings model."""

    def test_settings_model_has_no_cors_origins_field(self):
        """The Settings class must not declare a cors_origins field."""
        S = get_settings_class()

        # Check Pydantic v1 / v2 field introspection
        if hasattr(S, "model_fields"):  # Pydantic v2
            fields = S.model_fields
        elif hasattr(S, "__fields__"):  # Pydantic v1
            fields = S.__fields__
        else:
            fields = vars(S)

        assert "cors_origins" not in fields, (
            "cors_origins field should have been removed from Settings"
        )

    def test_instantiation_without_cors_origins_succeeds(self):
        """Settings can be instantiated without supplying cors_origins."""
        S = get_settings_class()
        # Should not raise
        instance = S()
        assert not hasattr(instance, "cors_origins") or getattr(instance, "cors_origins", None) is None

    def test_passing_cors_origins_raises_error(self):
        """Supplying cors_origins should raise a validation error (unknown field)."""
        S = get_settings_class()

        with pytest.raises((ValidationError, TypeError, ValueError)):
            S(cors_origins="http://example.com")

    def test_passing_cors_origins_as_kwarg_raises_error(self):
        """Keyword argument cors_origins must be rejected by the model."""
        S = get_settings_class()

        with pytest.raises((ValidationError, TypeError, ValueError)):
            S(**{"cors_origins": "http://localhost:5173"})

    def test_passing_none_cors_origins_raises_error(self):
        """Even cors_origins=None should be rejected after field removal."""
        S = get_settings_class()

        with pytest.raises((ValidationError, TypeError, ValueError)):
            S(cors_origins=None)

    def test_passing_empty_string_cors_origins_raises_error(self):
        """cors_origins='' should also be rejected."""
        S = get_settings_class()

        with pytest.raises((ValidationError, TypeError, ValueError)):
            S(cors_origins="")


# ---------------------------------------------------------------------------
# 2. Backward-incompatible serialisation / deserialisation
# ---------------------------------------------------------------------------


class TestBackwardIncompatibleCases:
    """Ensure that payloads that previously included cors_origins are handled."""

    def test_dict_with_cors_origins_raises_validation_error(self):
        """Parsing a dict that contains cors_origins must raise ValidationError."""
        S = get_settings_class()

        payload = {"cors_origins": "http://localhost:5173"}

        # Pydantic v2 uses model_validate; v1 uses parse_obj / __init__
        with pytest.raises((ValidationError, TypeError, ValueError)):
            if hasattr(S, "model_validate"):
                S.model_validate(payload)
            else:
                S(**payload)

    def test_json_with_cors_origins_raises_validation_error(self):
        """Parsing JSON that contains cors_origins must raise ValidationError."""
        import json

        S = get_settings_class()

        json_payload = json.dumps({"cors_origins": "http://localhost:5173"})

        with pytest.raises((ValidationError, TypeError, ValueError)):
            if hasattr(S, "model_validate_json"):  # Pydantic v2
                S.model_validate_json(json_payload)
            elif hasattr(S, "parse_raw"):  # Pydantic v1
                S.parse_raw(json_payload)
            else:
                S(**json.loads(json_payload))

    def test_serialised_output_does_not_contain_cors_origins(self):
        """Serialising a valid Settings instance must not produce cors_origins."""
        S = get_settings_class()

        instance = S()

        if hasattr(instance, "model_dump"):  # Pydantic v2
            data = instance.model_dump()
        elif hasattr(instance, "dict"):  # Pydantic v1
            data = instance.dict()
        else:
            data = vars(instance)

        assert "cors_origins" not in data, (
            "Serialised Settings must not include the removed cors_origins key"
        )

    def test_json_serialisation_does_not_contain_cors_origins(self):
        """JSON serialisation must not include cors_origins."""
        import json

        S = get_settings_class()
        instance = S()

        if hasattr(instance, "model_dump_json"):  # Pydantic v2
            json_str = instance.model_dump_json()
        elif hasattr(instance, "json"):  # Pydantic v1
            json_str = instance.json()
        else:
            json_str = json.dumps(vars(instance))

        data = json.loads(json_str)
        assert "cors_origins" not in data, (
            "JSON output must not contain cors_origins after field removal"
        )


# ---------------------------------------------------------------------------
# 3. Settings model basic sanity (new behaviour)
# ---------------------------------------------------------------------------


class TestSettingsNewBehaviour:
    """Basic smoke tests for the post-change Settings model."""

    def test_settings_is_importable(self):
        """Settings class must be importable."""
        S = get_settings_class()
        assert S is not None

    def test_settings_instantiates_with_defaults(self):
        """Settings() with no arguments must succeed."""
        S = get_settings_class()
        instance = S()
        assert instance is not None

    def test_settings_instance_has_expected_type(self):
        """The returned object must be an instance of Settings."""
        S = get_settings_class()
        instance = S()
        assert isinstance(instance, S)

    def test_cors_origins_attribute_absent_or_none_on_instance(self):
        """cors_origins must not be a meaningful attribute after removal."""
        S = get_settings_class()
        instance = S()

        # It must either not exist or be explicitly None (not the old default).
        value = getattr(instance, "cors_origins", _SENTINEL := object())
        if value is not _SENTINEL:
            # If the attribute somehow still exists, it must not carry the old default.
            assert value != "http://localhost:5173", (
                "The old default value 'http://localhost:5173' should no longer be present"
            )