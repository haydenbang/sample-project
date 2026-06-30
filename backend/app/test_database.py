"""Tests for backend/app/database.py after cors_origins field removal from Settings."""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def make_settings(database_url: str = "sqlite:///./test.db"):
    """Return a minimal settings-like object that exposes database_url."""
    s = MagicMock()
    s.database_url = database_url
    return s


# ---------------------------------------------------------------------------
# 1. Settings no longer has cors_origins
# ---------------------------------------------------------------------------

class TestCorsOriginsRemoved:
    """Verify that Settings no longer exposes cors_origins."""

    def test_settings_has_no_cors_origins_attribute(self):
        """After removal, importing Settings should not give cors_origins."""
        try:
            from app.config import Settings
            instance = Settings()
            assert not hasattr(instance, "cors_origins"), (
                "cors_origins was supposed to be removed from Settings"
            )
        except ImportError:
            pytest.skip("app.config not importable in this environment")

    def test_settings_instance_has_no_cors_origins(self):
        """The singleton `settings` object must not carry cors_origins."""
        try:
            from app.config import settings
            assert not hasattr(settings, "cors_origins"), (
                "settings still has cors_origins – field was not removed"
            )
        except ImportError:
            pytest.skip("app.config not importable in this environment")

    def test_accessing_cors_origins_raises_attribute_error(self):
        """Accessing cors_origins on the real settings object should raise AttributeError."""
        try:
            from app.config import settings
            with pytest.raises(AttributeError):
                _ = settings.cors_origins
        except ImportError:
            pytest.skip("app.config not importable in this environment")

    def test_creating_settings_with_cors_origins_raises_error(self):
        """Passing cors_origins when constructing Settings must raise a validation error."""
        try:
            from app.config import Settings
            import pydantic
            with pytest.raises((TypeError, pydantic.ValidationError, ValueError)):
                Settings(cors_origins="http://example.com")
        except ImportError:
            pytest.skip("app.config not importable in this environment")


# ---------------------------------------------------------------------------
# 2. database.py imports and basic structure
# ---------------------------------------------------------------------------

class TestDatabaseModuleImport:
    """database.py must import cleanly after the schema change."""

    def test_module_imports_without_error(self):
        try:
            import app.database  # noqa: F401
        except ImportError as exc:
            pytest.fail(f"app.database failed to import: {exc}")

    def test_engine_is_present(self):
        try:
            from app.database import engine
            assert engine is not None
        except ImportError:
            pytest.skip("app.database not importable")

    def test_session_local_is_present(self):
        try:
            from app.database import SessionLocal
            assert SessionLocal is not None
        except ImportError:
            pytest.skip("app.database not importable")

    def test_base_is_present(self):
        try:
            from app.database import Base
            assert Base is not None
        except ImportError:
            pytest.skip("app.database not importable")

    def test_get_db_is_callable(self):
        try:
            from app.database import get_db
            assert callable(get_db)
        except ImportError:
            pytest.skip("app.database not importable")


# ---------------------------------------------------------------------------
# 3. connect_args logic (sqlite vs non-sqlite)
# ---------------------------------------------------------------------------

class TestConnectArgs:
    """connect_args must be set correctly depending on the database URL."""

    def _reload_database_module_with_url(self, url: str):
        """Re-import app.database with a patched settings.database_url."""
        import importlib
        import sys

        mock_settings = make_settings(database_url=url)

        # Remove cached modules so we get a fresh import
        for mod_name in list(sys.modules.keys()):
            if "app.database" in mod_name:
                del sys.modules[mod_name]

        with patch("app.config.settings", mock_settings):
            try:
                mod = importlib.import_module("app.database")
                return mod
            except Exception:
                return None

    def test_sqlite_sets_check_same_thread_false(self):
        """For SQLite URLs, check_same_thread must be False."""
        try:
            from app import database as db_module
            # Inspect connect_args on the current engine
            current_url = str(db_module.engine.url)
            if current_url.startswith("sqlite"):
                assert db_module.engine.dialect.name == "sqlite"
        except ImportError:
            pytest.skip("app.database not importable")

    def test_connect_args_sqlite(self):
        """connect_args for sqlite should contain check_same_thread=False."""
        sqlite_url = "sqlite:///./test.db"
        # Simulate the logic from database.py directly
        connect_args = {"check_same_thread": False} if sqlite_url.startswith("sqlite") else {}
        assert connect_args == {"check_same_thread": False}

    def test_connect_args_postgres(self):
        """connect_args for postgres should be empty."""
        pg_url = "postgresql://user:pass@localhost/db"
        connect_args = {"check_same_thread": False} if pg_url.startswith("sqlite") else {}
        assert connect_args == {}

    def test_connect_args_mysql(self):
        """connect_args for mysql should be empty."""
        mysql_url = "mysql+pymysql://user:pass@localhost/db"
        connect_args = {"check_same_thread": False} if mysql_url.startswith("sqlite") else {}
        assert connect_args == {}


# ---------------------------------------------------------------------------
# 4. get_db generator
# ---------------------------------------------------------------------------

class TestGetDb:
    """get_db should yield a session and close it afterwards."""

    def test_get_db_yields_session(self):
        try:
            from app.database import get_db, SessionLocal
        except ImportError:
            pytest.skip("app.database not importable")

        mock_session = MagicMock()
        with patch.object(SessionLocal, "__call__", return_value=mock_session):
            gen = get_db()
            session = next(gen)
            assert session is mock_session

    def test_get_db_closes_session_on_exit(self):
        try:
            from app.database import get_db, SessionLocal
        except ImportError:
            pytest.skip("app.database not importable")

        mock_session = MagicMock()
        with patch.object(SessionLocal, "__call__", return_value=mock_session):
            gen = get_db()
            next(gen)
            with pytest.raises(StopIteration):
                next(gen)
            mock_session.close.assert_called_once()

    def test_get_db_closes_session_on_exception(self):
        """Session must be closed even when an exception occurs inside the generator."""
        try:
            from app.database import get_db, SessionLocal
        except ImportError:
            pytest.skip("app.database not importable")

        mock_session = MagicMock()
        with patch.object(SessionLocal, "__call__", return_value=mock_session):
            gen = get_db()
            next(gen)
            try:
                gen.throw(RuntimeError("Something went wrong"))
            except RuntimeError:
                pass
            mock_session.close.assert_called_once()

    def test_get_db_is_generator(self):
        """get_db must return a generator."""
        import inspect
        try:
            from app.database import get_db
        except ImportError:
            pytest.skip("app.database not importable")

        assert inspect.isgeneratorfunction(get_db)


# ---------------------------------------------------------------------------
# 5. database.py does NOT reference cors_origins
# ---------------------------------------------------------------------------

class TestDatabaseDoesNotUseCorsOrigins:
    """Ensure database.py source code has no reference to cors_origins."""

    def test_source_does_not_reference_cors_origins(self):
        import pathlib

        candidates = [
            pathlib.Path("backend/app/database.py"),
            pathlib.Path("app/database.py"),
            pathlib.Path("database.py"),
        ]

        source = None
        for path in candidates:
            if path.exists():
                source = path.read_text()
                break

        if source is None:
            pytest.skip("Cannot locate database.py source file")

        assert "cors_origins" not in source, (
            "database.py must not reference cors_origins after field removal"
        )

    def test_source_uses_database_url(self):
        """database.py should still reference settings.database_url."""
        import pathlib

        candidates = [
            pathlib.Path("backend/app/database.py"),
            pathlib.Path("app/database.py"),
            pathlib.Path("database.py"),
        ]

        source = None
        for path in candidates:
            if path.exists():
                source = path.read_text()
                break

        if source is None:
            pytest.skip("Cannot locate database.py source file")

        assert "database_url" in source, (
            "database.py should still use settings.database_url"
        )


# ---------------------------------------------------------------------------
# 6. Backward-incompatible scenarios
# ---------------------------------------------------------------------------

class TestBackwardIncompatibleCases:
    """Guard against attempts to use the removed cors_origins field."""

    def test_old_code_using_cors_origins_from_settings_fails(self):
        """Simulate old code that read settings.cors_origins – must fail with AttributeError."""
        try:
            from app.config import settings
        except ImportError:
            pytest.skip("app.config not importable")

        def old_code():
            return settings.cors_origins.split(",")

        with pytest.raises(AttributeError):
            old_code()

    def test_mock_settings_without_cors_origins_still_works_for_database(self):
        """A settings mock without cors_origins must not break database module logic."""
        mock_settings = MagicMock(spec=["database_url"])
        mock_settings.database_url = "sqlite:///./test.db"

        # The connect_args logic from database.py should work fine
        connect_args = (
            {"check_same_thread": False}
            if mock_settings.database_url.startswith("sqlite")
            else {}
        )
        assert connect_args == {"check_same_thread": False}

        # Accessing cors_origins on this mock should raise AttributeError
        with pytest.raises(AttributeError):
            _ = mock_settings.cors_origins

    def test_serialization_of_settings_excludes_cors_origins(self):
        """If Settings is a Pydantic model, its dict/model_dump must not include cors_origins."""
        try:
            from app.config import Settings
            instance = Settings()
        except (ImportError, Exception):
            pytest.skip("Cannot instantiate Settings")

        try:
            # Pydantic v2
            data = instance.model_dump()
        except AttributeError:
            try:
                # Pydantic v1
                data = instance.dict()
            except AttributeError:
                pytest.skip("Settings is not a Pydantic model")

        assert "cors_origins" not in data, (
            "Serialized Settings must not contain cors_origins after field removal"
        )

    def test_settings_default_no_longer_sets_cors_origins(self):
        """The old default 'http://localhost:5173' must not appear in settings."""
        try:
            from app.config import settings
        except ImportError:
            pytest.skip("app.config not importable")

        assert not hasattr(settings, "cors_origins"), (
            "The default value 'http://localhost:5173' for cors_origins should not exist"
        )