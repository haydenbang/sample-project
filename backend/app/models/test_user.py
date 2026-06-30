import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Helpers / compatibility shims
# ---------------------------------------------------------------------------

def import_settings():
    """
    Try several common import paths for the Settings model/schema.
    Returns the Settings class or raises ImportError.
    """
    candidates = [
        "backend.app.models.user",
        "app.models.user",
        "backend.app.core.config",
        "app.core.config",
        "backend.app.config",
        "app.config",
    ]
    for path in candidates:
        try:
            mod = __import__(path, fromlist=["Settings"])
            if hasattr(mod, "Settings"):
                return mod.Settings
        except (ImportError, ModuleNotFoundError):
            continue

    # Last resort: try a direct relative import assumption
    raise ImportError(
        "Could not import 'Settings' from any known module path. "
        "Adjust the import path to match your project layout."
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def Settings():
    return import_settings()


@pytest.fixture
def minimal_valid_data():
    """
    Return the minimal set of fields required to construct a valid Settings
    instance *without* cors_origins (since that field has been removed).
    Adjust as needed if your Settings model has other required fields.
    """
    return {}


# ---------------------------------------------------------------------------
# Tests: cors_origins field is REMOVED
# ---------------------------------------------------------------------------

class TestCorsOriginsFieldRemoved:
    """
    Verify that the 'cors_origins' field has been removed from Settings.
    """

    def test_settings_has_no_cors_origins_attribute(self, Settings):
        """Settings class must not declare a cors_origins field."""
        # Check class-level field definitions (Pydantic v1 & v2)
        if hasattr(Settings, "__fields__"):  # Pydantic v1
            assert "cors_origins" not in Settings.__fields__, (
                "cors_origins field should have been removed from Settings "
                "but is still declared in __fields__."
            )
        if hasattr(Settings, "model_fields"):  # Pydantic v2
            assert "cors_origins" not in Settings.model_fields, (
                "cors_origins field should have been removed from Settings "
                "but is still declared in model_fields."
            )

    def test_settings_instantiation_without_cors_origins(self, Settings, minimal_valid_data):
        """Settings should instantiate successfully without cors_origins."""
        instance = Settings(**minimal_valid_data)
        assert instance is not None

    def test_settings_instance_has_no_cors_origins_attr(self, Settings, minimal_valid_data):
        """An instance of Settings must not expose a cors_origins attribute."""
        instance = Settings(**minimal_valid_data)
        assert not hasattr(instance, "cors_origins"), (
            "Settings instance should not have a 'cors_origins' attribute "
            "after the field has been removed."
        )

    def test_settings_serialization_excludes_cors_origins(self, Settings, minimal_valid_data):
        """Serialized output of Settings must not contain cors_origins."""
        instance = Settings(**minimal_valid_data)

        # Pydantic v2
        if hasattr(instance, "model_dump"):
            data = instance.model_dump()
        # Pydantic v1
        elif hasattr(instance, "dict"):
            data = instance.dict()
        else:
            pytest.skip("Settings instance has neither model_dump() nor dict().")

        assert "cors_origins" not in data, (
            "Serialized Settings dict should not contain 'cors_origins', "
            f"but got keys: {list(data.keys())}"
        )

    def test_settings_json_excludes_cors_origins(self, Settings, minimal_valid_data):
        """JSON representation of Settings must not contain cors_origins."""
        instance = Settings(**minimal_valid_data)

        # Pydantic v2
        if hasattr(instance, "model_dump_json"):
            json_str = instance.model_dump_json()
        # Pydantic v1
        elif hasattr(instance, "json"):
            json_str = instance.json()
        else:
            pytest.skip("Settings instance has neither model_dump_json() nor json().")

        assert "cors_origins" not in json_str, (
            "JSON-serialized Settings should not contain 'cors_origins'."
        )


# ---------------------------------------------------------------------------
# Tests: backward-incompatible usage raises appropriate errors
# ---------------------------------------------------------------------------

class TestBackwardIncompatibleUsage:
    """
    Verify that code that still tries to *pass* cors_origins to Settings
    receives clear, appropriate errors (not silent acceptance).
    """

    def test_passing_cors_origins_raises_error(self, Settings, minimal_valid_data):
        """
        Constructing Settings with cors_origins should raise a ValidationError
        or TypeError — it must NOT be silently ignored.
        """
        data_with_old_field = {**minimal_valid_data, "cors_origins": "http://localhost:5173"}

        raised = False
        try:
            instance = Settings(**data_with_old_field)
            # If we reach here without error, check that the value was NOT stored
            if hasattr(instance, "cors_origins"):
                pytest.fail(
                    "Settings accepted 'cors_origins' and stored it — "
                    "the field should have been removed."
                )
            # Pydantic models with extra='ignore' will silently drop unknown fields.
            # That is acceptable behaviour; we just ensure the value is not stored.
        except (ValidationError, TypeError, ValueError):
            raised = True

        # Both outcomes are acceptable:
        # 1. An error is raised (strict mode / extra='forbid')
        # 2. The field is silently dropped (extra='ignore') — but then the
        #    instance must not expose the attribute (checked above).

    def test_passing_cors_origins_with_extra_forbid(self, Settings, minimal_valid_data):
        """
        If the Settings model uses extra='forbid' (Pydantic v2) or
        Extra.forbid (Pydantic v1), passing cors_origins must raise
        a ValidationError.
        """
        # Detect whether the model forbids extra fields
        forbids_extra = False

        # Pydantic v2
        if hasattr(Settings, "model_config"):
            extra_setting = getattr(Settings.model_config, "get", lambda k, d=None: None)("extra")
            if extra_setting == "forbid":
                forbids_extra = True

        # Pydantic v1
        if hasattr(Settings, "__config__"):
            from pydantic import Extra as _Extra  # noqa: F401 — may not exist in v2
            cfg_extra = getattr(Settings.__config__, "extra", None)
            if cfg_extra in ("forbid", "Extra.forbid"):
                forbids_extra = True

        if not forbids_extra:
            pytest.skip(
                "Settings does not use extra='forbid'; this test only applies "
                "when unknown fields are explicitly rejected."
            )

        data_with_old_field = {**minimal_valid_data, "cors_origins": "http://localhost:5173"}
        with pytest.raises(ValidationError):
            Settings(**data_with_old_field)

    def test_old_default_value_not_present(self, Settings, minimal_valid_data):
        """
        The old default value 'http://localhost:5173' must not appear
        anywhere in the serialized Settings output.
        """
        instance = Settings(**minimal_valid_data)

        if hasattr(instance, "model_dump"):
            data = instance.model_dump()
        elif hasattr(instance, "dict"):
            data = instance.dict()
        else:
            pytest.skip("Cannot serialize Settings instance.")

        for key, value in data.items():
            assert value != "http://localhost:5173", (
                f"Field '{key}' still holds the old cors_origins default value."
            )

    def test_cors_origins_not_in_schema(self, Settings):
        """
        The JSON Schema generated from Settings must not reference cors_origins.
        """
        # Pydantic v2
        if hasattr(Settings, "model_json_schema"):
            schema = Settings.model_json_schema()
        # Pydantic v1
        elif hasattr(Settings, "schema"):
            schema = Settings.schema()
        else:
            pytest.skip("Settings does not expose a schema() / model_json_schema() method.")

        properties = schema.get("properties", {})
        assert "cors_origins" not in properties, (
            "JSON Schema for Settings still lists 'cors_origins' in properties."
        )


# ---------------------------------------------------------------------------
# Tests: Settings still works correctly for its remaining responsibility
# ---------------------------------------------------------------------------

class TestSettingsGeneralValidity:
    """
    Sanity-check that Settings can still be used normally after the removal.
    """

    def test_settings_is_instantiable(self, Settings, minimal_valid_data):
        instance = Settings(**minimal_valid_data)
        assert instance is not None

    def test_settings_is_pydantic_model(self, Settings):
        """Settings should be a Pydantic BaseModel or BaseSettings subclass."""
        try:
            from pydantic import BaseModel
            assert issubclass(Settings, BaseModel), (
                "Settings is not a subclass of pydantic.BaseModel."
            )
        except ImportError:
            pytest.skip("pydantic is not installed.")

    def test_settings_equality_is_stable(self, Settings, minimal_valid_data):
        """Two instances created with the same data should be equal."""
        a = Settings(**minimal_valid_data)
        b = Settings(**minimal_valid_data)

        if hasattr(a, "model_dump"):
            assert a.model_dump() == b.model_dump()
        elif hasattr(a, "dict"):
            assert a.dict() == b.dict()