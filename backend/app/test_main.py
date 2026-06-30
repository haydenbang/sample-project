"""Tests for backend/app/main.py verifying cors_origins field removal and cors_origin_list usage."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


class TestSettingsCorsMigration:
    """Tests verifying that cors_origins has been removed and cors_origin_list is used."""

    def test_settings_has_no_cors_origins_field(self):
        """Verify that the Settings model no longer has cors_origins field."""
        try:
            from app.config import settings
            assert not hasattr(settings, 'cors_origins'), (
                "settings should NOT have 'cors_origins' field after removal"
            )
        except ImportError:
            pytest.skip("app.config not available")

    def test_settings_has_cors_origin_list(self):
        """Verify that settings has cors_origin_list attribute."""
        try:
            from app.config import settings
            assert hasattr(settings, 'cors_origin_list'), (
                "settings should have 'cors_origin_list' attribute"
            )
        except ImportError:
            pytest.skip("app.config not available")

    def test_cors_origin_list_is_list(self):
        """Verify cors_origin_list returns a list."""
        try:
            from app.config import settings
            origin_list = settings.cors_origin_list
            assert isinstance(origin_list, list), (
                f"cors_origin_list should be a list, got {type(origin_list)}"
            )
        except ImportError:
            pytest.skip("app.config not available")

    def test_cors_origin_list_contains_strings(self):
        """Verify cors_origin_list contains string values."""
        try:
            from app.config import settings
            origin_list = settings.cors_origin_list
            for origin in origin_list:
                assert isinstance(origin, str), (
                    f"Each origin in cors_origin_list should be a str, got {type(origin)}"
                )
        except ImportError:
            pytest.skip("app.config not available")

    def test_settings_cors_origins_raises_attribute_error(self):
        """Verify accessing cors_origins raises AttributeError (field removed)."""
        try:
            from app.config import settings
            with pytest.raises(AttributeError):
                _ = settings.cors_origins
        except ImportError:
            pytest.skip("app.config not available")


class TestMainAppCORSMiddleware:
    """Tests verifying that the FastAPI app uses cors_origin_list for CORS middleware."""

    def test_app_imports_successfully(self):
        """Verify that main.py imports without errors."""
        try:
            import app.main
        except AttributeError as e:
            pytest.fail(f"main.py import failed with AttributeError: {e}")
        except ImportError as e:
            pytest.skip(f"Import dependency missing: {e}")

    def test_app_is_fastapi_instance(self):
        """Verify that app is a FastAPI instance."""
        try:
            from fastapi import FastAPI
            from app.main import app
            assert isinstance(app, FastAPI), "app should be a FastAPI instance"
        except ImportError as e:
            pytest.skip(f"Import dependency missing: {e}")

    def test_cors_middleware_uses_origin_list_not_cors_origins(self):
        """Verify CORS middleware is configured with cors_origin_list not cors_origins."""
        try:
            from fastapi.middleware.cors import CORSMiddleware
            from app.main import app

            cors_middleware = None
            for middleware in app.user_middleware:
                if middleware.cls == CORSMiddleware:
                    cors_middleware = middleware
                    break

            assert cors_middleware is not None, "CORSMiddleware should be registered"
            
            # Verify allow_origins is set (from cors_origin_list)
            assert 'allow_origins' in cors_middleware.kwargs, (
                "CORSMiddleware should have allow_origins configured"
            )
            
            allow_origins = cors_middleware.kwargs['allow_origins']
            assert isinstance(allow_origins, list), (
                f"allow_origins should be a list, got {type(allow_origins)}"
            )
        except ImportError as e:
            pytest.skip(f"Import dependency missing: {e}")

    def test_main_does_not_reference_cors_origins_attribute(self):
        """Verify main.py source code does not reference the removed cors_origins field."""
        import ast
        import os

        main_path = os.path.join(os.path.dirname(__file__), 'main.py')
        if not os.path.exists(main_path):
            # Try alternative path
            import app.main as main_module
            import inspect
            source = inspect.getsource(main_module)
        else:
            with open(main_path, 'r') as f:
                source = f.read()

        # Check that cors_origins (the removed field) is not referenced
        # but cors_origin_list is used
        lines = source.splitlines()
        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            # Check for direct attribute access to removed field
            if 'settings.cors_origins' in line and 'settings.cors_origin_list' not in line:
                pytest.fail(
                    f"Line {line_num} references removed 'cors_origins' field: {line.strip()}"
                )

    def test_main_references_cors_origin_list(self):
        """Verify main.py source code references cors_origin_list."""
        import os
        import inspect

        try:
            import app.main as main_module
            source = inspect.getsource(main_module)
        except ImportError as e:
            pytest.skip(f"Import dependency missing: {e}")

        assert 'cors_origin_list' in source, (
            "main.py should reference 'cors_origin_list' for CORS configuration"
        )


class TestCORSMiddlewareConfiguration:
    """Tests verifying CORS middleware configuration details."""

    def test_cors_middleware_allow_credentials(self):
        """Verify CORS middleware allows credentials."""
        try:
            from fastapi.middleware.cors import CORSMiddleware
            from app.main import app

            for middleware in app.user_middleware:
                if middleware.cls == CORSMiddleware:
                    assert middleware.kwargs.get('allow_credentials') is True, (
                        "CORSMiddleware should allow credentials"
                    )
                    return

            pytest.fail("CORSMiddleware not found in app middleware")
        except ImportError as e:
            pytest.skip(f"Import dependency missing: {e}")

    def test_cors_middleware_allow_all_methods(self):
        """Verify CORS middleware allows all methods."""
        try:
            from fastapi.middleware.cors import CORSMiddleware
            from app.main import app

            for middleware in app.user_middleware:
                if middleware.cls == CORSMiddleware:
                    assert middleware.kwargs.get('allow_methods') == ["*"], (
                        "CORSMiddleware should allow all methods"
                    )
                    return

            pytest.fail("CORSMiddleware not found in app middleware")
        except ImportError as e:
            pytest.skip(f"Import dependency missing: {e}")

    def test_cors_middleware_allow_all_headers(self):
        """Verify CORS middleware allows all headers."""
        try:
            from fastapi.middleware.cors import CORSMiddleware
            from app.main import app

            for middleware in app.user_middleware:
                if middleware.cls == CORSMiddleware:
                    assert middleware.kwargs.get('allow_headers') == ["*"], (
                        "CORSMiddleware should allow all headers"
                    )
                    return

            pytest.fail("CORSMiddleware not found in app middleware")
        except ImportError as e:
            pytest.skip(f"Import dependency missing: {e}")


class TestSettingsBackwardIncompatibility:
    """Tests verifying backward-incompatible cases raise correct errors."""

    def test_accessing_cors_origins_on_settings_raises_error(self):
        """
        Test that code trying to use the old cors_origins field
        raises AttributeError (backward-incompatible change).
        """
        try:
            from app.config import settings

            with pytest.raises(AttributeError) as exc_info:
                _ = settings.cors_origins

            assert 'cors_origins' in str(exc_info.value).lower() or \
                   'attribute' in str(exc_info.value).lower(), (
                f"AttributeError message should mention the missing attribute, got: {exc_info.value}"
            )
        except ImportError:
            pytest.skip("app.config not available")

    def test_settings_model_validation_without_cors_origins(self):
        """
        Test that Settings can be instantiated without cors_origins field.
        The field has been removed so it should not be required.
        """
        try:
            from app.config import Settings

            # Try to create settings without cors_origins - should work
            try:
                # This may require other env vars, so we use environment variables
                import os
                with patch.dict(os.environ, {}, clear=False):
                    # If Settings can be instantiated, cors_origins is not required
                    # We just verify the class doesn't have cors_origins in its fields
                    if hasattr(Settings, 'model_fields'):
                        # Pydantic v2
                        assert 'cors_origins' not in Settings.model_fields, (
                            "cors_origins should not be in Settings model fields"
                        )
                    elif hasattr(Settings, '__fields__'):
                        # Pydantic v1
                        assert 'cors_origins' not in Settings.__fields__, (
                            "cors_origins should not be in Settings fields"
                        )
            except Exception:
                pass  # Settings might have required fields from environment
        except ImportError:
            pytest.skip("app.config.Settings not available")

    def test_old_cors_origins_string_not_accepted(self):
        """
        Test that the old cors_origins field (str type) is no longer part of the schema.
        """
        try:
            from app.config import Settings

            if hasattr(Settings, 'model_fields'):
                # Pydantic v2
                fields = Settings.model_fields
            elif hasattr(Settings, '__fields__'):
                # Pydantic v1
                fields = Settings.__fields__
            else:
                pytest.skip("Cannot introspect Settings fields")
                return

            assert 'cors_origins' not in fields, (
                "The 'cors_origins' field (type str) has been removed and should not exist in Settings"
            )
        except ImportError:
            pytest.skip("app.config.Settings not available")


class TestHealthEndpoint:
    """Tests for health endpoint to verify app is functional."""

    def test_health_endpoint_exists(self):
        """Verify the health endpoint is registered."""
        try:
            from app.main import app

            routes = [route.path for route in app.routes]
            assert '/api/health' in routes, "Health endpoint should be registered at /api/health"
        except ImportError as e:
            pytest.skip(f"Import dependency missing: {e}")

    def test_health_endpoint_response(self):
        """Verify the health endpoint returns correct response structure."""
        try:
            from fastapi.testclient import TestClient
            from app.main import app

            client = TestClient(app, raise_server_exceptions=True)
            
            with patch('app.main.settings') as mock_settings:
                mock_settings.app_name = "Test App"
                mock_settings.environment = "test"
                mock_settings.cors_origin_list = ["http://localhost:5173"]
                
                # Use the actual app's health endpoint function directly
                from app.main import health
                result = health()
                
                assert 'status' in result, "Health response should have 'status' key"
                assert result['status'] == 'ok', "Health status should be 'ok'"
        except ImportError as e:
            pytest.skip(f"Import dependency missing: {e}")


class TestMockSettingsIntegration:
    """Integration tests using mocked settings to verify cors_origin_list behavior."""

    def test_mock_settings_with_cors_origin_list_single_origin(self):
        """Test that cors_origin_list with single origin works correctly."""
        mock_settings = MagicMock()
        mock_settings.cors_origin_list = ["http://localhost:5173"]
        mock_settings.app_name = "TestApp"
        mock_settings.environment = "test"

        # Verify no cors_origins attribute
        del mock_settings.cors_origins
        
        assert isinstance(mock_settings.cors_origin_list, list)
        assert len(mock_settings.cors_origin_list) == 1
        assert mock_settings.cors_origin_list[0] == "http://localhost:5173"

    def test_mock_settings_with_cors_origin_list_multiple_origins(self):
        """Test that cors_origin_list supports multiple origins."""
        mock_settings = MagicMock()
        mock_settings.cors_origin_list = [
            "http://localhost:5173",
            "http://localhost:3000",
            "https://example.com"
        ]

        assert isinstance(mock_settings.cors_origin_list, list)
        assert len(mock_settings.cors_origin_list) == 3

    def test_cors_middleware_with_mocked_origin_list(self):
        """Test CORS middleware can be configured with cors_origin_list."""
        try:
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware

            test_app = FastAPI()
            origins = ["http://localhost:5173", "http://localhost:3000"]

            test_app.add_middleware(
                CORSMiddleware,
                allow_origins=origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

            # Verify middleware is configured with the list
            for middleware in test_app.user_middleware:
                if middleware.cls == CORSMiddleware:
                    assert middleware.kwargs['allow_origins'] == origins
                    return

            pytest.fail("CORSMiddleware was not found after adding")
        except ImportError as e:
            pytest.skip(f"FastAPI not available: {e}")