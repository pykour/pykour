"""Tests for pykour.config module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch


from pykour.config import (
    PykourConfig,
    find_config_file,
    load_config,
)
from pykour.config.env import apply_env_overrides
from pykour.config.loader import dict_to_config, load_toml


class TestPykourConfigDefaults:
    """Test default configuration values."""

    def test_default_config(self) -> None:
        """Test that PykourConfig has correct defaults."""
        config = PykourConfig()

        assert config.app.routes_dir == "routes"
        assert config.app.debug is False
        assert config.openapi.title == "Pykour API"
        assert config.openapi.version == "1.0.0"
        assert config.health.url == "/health"
        assert config.metrics.url == "/metrics"
        assert config.database.url is None
        assert config.cache.url is None

    def test_default_middleware_config(self) -> None:
        """Test that middleware config has correct defaults."""
        config = PykourConfig()

        assert config.middleware.cors.enabled is False
        assert config.middleware.jwt.enabled is False
        assert config.middleware.rate_limit.enabled is False
        assert config.middleware.security.enabled is False
        assert config.middleware.csrf.enabled is False


class TestLoadToml:
    """Test TOML file loading."""

    def test_load_simple_toml(self) -> None:
        """Test loading a simple TOML file."""
        toml_content = """
[app]
routes_dir = "my_routes"
debug = true

[openapi]
title = "My API"
version = "2.0.0"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()

            data = load_toml(Path(f.name))
            assert data["app"]["routes_dir"] == "my_routes"
            assert data["app"]["debug"] is True
            assert data["openapi"]["title"] == "My API"

            os.unlink(f.name)

    def test_load_middleware_toml(self) -> None:
        """Test loading TOML with middleware configuration."""
        toml_content = """
[middleware.cors]
enabled = true
allow_origins = ["https://example.com"]
allow_methods = ["GET", "POST"]

[middleware.jwt]
enabled = true
algorithm = "HS256"
exclude_paths = ["/health", "/docs"]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()

            data = load_toml(Path(f.name))
            assert data["middleware"]["cors"]["enabled"] is True
            assert data["middleware"]["cors"]["allow_origins"] == [
                "https://example.com"
            ]
            assert data["middleware"]["jwt"]["enabled"] is True

            os.unlink(f.name)


class TestDictToConfig:
    """Test dictionary to config conversion."""

    def test_convert_app_config(self) -> None:
        """Test converting app section."""
        data = {"app": {"routes_dir": "api", "debug": True}}
        config = dict_to_config(data)

        assert config.app.routes_dir == "api"
        assert config.app.debug is True

    def test_convert_openapi_config(self) -> None:
        """Test converting openapi section."""
        data = {
            "openapi": {
                "title": "Test API",
                "version": "3.0.0",
                "description": "Test description",
                "docs_url": "/api-docs",
            }
        }
        config = dict_to_config(data)

        assert config.openapi.title == "Test API"
        assert config.openapi.version == "3.0.0"
        assert config.openapi.description == "Test description"
        assert config.openapi.docs_url == "/api-docs"

    def test_convert_database_config(self) -> None:
        """Test converting database section."""
        data = {
            "database": {
                "url": "postgresql://localhost/db",
                "min_size": 5,
                "max_size": 20,
            }
        }
        config = dict_to_config(data)

        assert config.database.url == "postgresql://localhost/db"
        assert config.database.min_size == 5
        assert config.database.max_size == 20

    def test_convert_middleware_config(self) -> None:
        """Test converting middleware section."""
        data = {
            "middleware": {
                "cors": {
                    "enabled": True,
                    "allow_origins": ["*"],
                    "max_age": 3600,
                },
                "rate_limit": {
                    "enabled": True,
                    "requests_per_second": 5.0,
                    "path_configs": {
                        "/api/login": {
                            "requests_per_second": 1.0,
                            "burst_size": 3,
                        }
                    },
                },
            }
        }
        config = dict_to_config(data)

        assert config.middleware.cors.enabled is True
        assert config.middleware.cors.allow_origins == ["*"]
        assert config.middleware.cors.max_age == 3600
        assert config.middleware.rate_limit.enabled is True
        assert config.middleware.rate_limit.requests_per_second == 5.0
        assert "/api/login" in config.middleware.rate_limit.path_configs
        assert (
            config.middleware.rate_limit.path_configs["/api/login"].requests_per_second
            == 1.0
        )


class TestEnvOverrides:
    """Test environment variable overrides."""

    def test_debug_env_override(self) -> None:
        """Test PYKOUR_DEBUG environment variable."""
        config = PykourConfig()
        assert config.app.debug is False

        with patch.dict(os.environ, {"PYKOUR_DEBUG": "true"}):
            config = apply_env_overrides(config)
            assert config.app.debug is True

    def test_database_url_env_override(self) -> None:
        """Test PYKOUR_DATABASE_URL environment variable."""
        config = PykourConfig()
        assert config.database.url is None

        with patch.dict(os.environ, {"PYKOUR_DATABASE_URL": "sqlite:///test.db"}):
            config = apply_env_overrides(config)
            assert config.database.url == "sqlite:///test.db"

    def test_cache_url_env_override(self) -> None:
        """Test PYKOUR_CACHE_URL environment variable."""
        config = PykourConfig()
        assert config.cache.url is None

        with patch.dict(os.environ, {"PYKOUR_CACHE_URL": "valkey://localhost:6379"}):
            config = apply_env_overrides(config)
            assert config.cache.url == "valkey://localhost:6379"

    def test_jwt_secret_key_env_override(self) -> None:
        """Test PYKOUR_JWT_SECRET_KEY environment variable."""
        config = PykourConfig()
        assert config.middleware.jwt.secret_key is None

        with patch.dict(os.environ, {"PYKOUR_JWT_SECRET_KEY": "my-secret"}):
            config = apply_env_overrides(config)
            assert config.middleware.jwt.secret_key == "my-secret"


class TestFindConfigFile:
    """Test config file discovery."""

    def test_find_config_in_current_dir(self) -> None:
        """Test finding config file in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "pykour.toml"
            config_path.write_text("[app]\ndebug = true\n")

            found = find_config_file(Path(tmpdir))
            # Resolve both paths to handle symlinks (e.g., /var -> /private/var on macOS)
            assert found is not None
            assert found.resolve() == config_path.resolve()

    def test_find_config_in_parent_dir(self) -> None:
        """Test finding config file in parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parent_dir = Path(tmpdir)
            child_dir = parent_dir / "subdir"
            child_dir.mkdir()

            config_path = parent_dir / "pykour.toml"
            config_path.write_text("[app]\ndebug = true\n")

            found = find_config_file(child_dir)
            # Resolve both paths to handle symlinks (e.g., /var -> /private/var on macOS)
            assert found is not None
            assert found.resolve() == config_path.resolve()

    def test_no_config_file(self) -> None:
        """Test when no config file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            found = find_config_file(Path(tmpdir))
            assert found is None


class TestLoadConfig:
    """Test the main load_config function."""

    def test_load_config_with_explicit_file(self) -> None:
        """Test loading config with explicit file path."""
        toml_content = """
[app]
routes_dir = "custom_routes"
debug = true

[openapi]
title = "Custom API"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()

            config = load_config(config_file=f.name)
            assert config.app.routes_dir == "custom_routes"
            assert config.app.debug is True
            assert config.openapi.title == "Custom API"

            os.unlink(f.name)

    def test_load_config_env_override(self) -> None:
        """Test that env vars override config file."""
        toml_content = """
[app]
debug = false

[database]
url = "sqlite:///file.db"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()

            with patch.dict(
                os.environ,
                {
                    "PYKOUR_DEBUG": "true",
                    "PYKOUR_DATABASE_URL": "postgresql://localhost/db",
                },
            ):
                config = load_config(config_file=f.name)
                # Env vars should override file values
                assert config.app.debug is True
                assert config.database.url == "postgresql://localhost/db"

            os.unlink(f.name)

    def test_load_config_auto_discover_disabled(self) -> None:
        """Test loading config with auto-discover disabled."""
        config = load_config(auto_discover=False)
        # Should use defaults
        assert config.app.routes_dir == "routes"
        assert config.openapi.title == "Pykour API"

    def test_load_config_env_file_path(self) -> None:
        """Test PYKOUR_CONFIG_FILE environment variable."""
        toml_content = """
[app]
routes_dir = "env_routes"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()

            with patch.dict(os.environ, {"PYKOUR_CONFIG_FILE": f.name}):
                config = load_config(auto_discover=False)
                assert config.app.routes_dir == "env_routes"

            os.unlink(f.name)


class TestFullTomlConfig:
    """Test loading a full TOML configuration."""

    def test_load_full_config(self) -> None:
        """Test loading a complete configuration file."""
        toml_content = """
[app]
routes_dir = "api/routes"
debug = true

[openapi]
title = "Full Test API"
version = "2.5.0"
description = "A full test API"
docs_url = "/swagger"
openapi_url = "/api.json"
redoc_url = "/documentation"

[health]
url = "/healthz"
include_details = true

[metrics]
url = "/prometheus"
enabled = true
namespace = "myapp"

[database]
url = "postgresql://user:pass@localhost:5432/mydb"
min_size = 2
max_size = 15

[cache]
url = "valkey://localhost:6379/1"
prefix = "myapp:"

[logging]
format = "json"
level = "DEBUG"

[middleware.cors]
enabled = true
allow_origins = ["https://example.com", "https://app.example.com"]
allow_methods = ["GET", "POST", "PUT", "DELETE"]
allow_credentials = true
max_age = 7200

[middleware.jwt]
enabled = false
algorithm = "HS256"
exclude_paths = ["/health", "/docs", "/api/auth"]

[middleware.rate_limit]
enabled = true
requests_per_second = 100.0
burst_size = 200
exclude_paths = ["/health"]

[middleware.security]
enabled = true
hsts_max_age = 63072000
x_frame_options = "SAMEORIGIN"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()

            config = load_config(config_file=f.name)

            # App
            assert config.app.routes_dir == "api/routes"
            assert config.app.debug is True

            # OpenAPI
            assert config.openapi.title == "Full Test API"
            assert config.openapi.version == "2.5.0"
            assert config.openapi.docs_url == "/swagger"

            # Health
            assert config.health.url == "/healthz"
            assert config.health.include_details is True

            # Metrics
            assert config.metrics.url == "/prometheus"
            assert config.metrics.enabled is True

            # Database
            assert config.database.url == "postgresql://user:pass@localhost:5432/mydb"
            assert config.database.min_size == 2
            assert config.database.max_size == 15

            # Cache
            assert config.cache.url == "valkey://localhost:6379/1"
            assert config.cache.prefix == "myapp:"

            # Logging
            assert config.logging.format == "json"
            assert config.logging.level == "DEBUG"

            # CORS
            assert config.middleware.cors.enabled is True
            assert "https://example.com" in config.middleware.cors.allow_origins
            assert config.middleware.cors.allow_credentials is True

            # JWT
            assert config.middleware.jwt.enabled is False

            # Rate Limit
            assert config.middleware.rate_limit.enabled is True
            assert config.middleware.rate_limit.requests_per_second == 100.0

            # Security
            assert config.middleware.security.enabled is True
            assert config.middleware.security.x_frame_options == "SAMEORIGIN"

            os.unlink(f.name)
