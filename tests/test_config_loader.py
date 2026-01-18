"""Tests for configuration loading and models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pykour.config.loader import (
    DEFAULT_CONFIG_FILE,
    dict_to_config,
    find_config_file,
    load_config,
    load_toml,
)
from pykour.config.models import (
    AppConfig,
    CacheConfig,
    CORSMiddlewareConfig,
    CSPConfig,
    CSRFMiddlewareConfig,
    DatabaseConfig,
    HealthConfig,
    JWTMiddlewareConfig,
    LoggingConfig,
    LoggingMiddlewareConfig,
    MetricsConfigModel,
    MiddlewareConfig,
    OpenAPIConfigModel,
    PykourConfig,
    RateLimitMiddlewareConfig,
    SecurityMiddlewareConfig,
    SizeLimitMiddlewareConfig,
    TraceMiddlewareConfig,
)


class TestFindConfigFile:
    """Tests for find_config_file function."""

    def test_find_in_current_dir(self, tmp_path: Path) -> None:
        """Find config file in current directory."""
        config_file = tmp_path / DEFAULT_CONFIG_FILE
        config_file.write_text("[app]\n")

        result = find_config_file(tmp_path)
        assert result == config_file

    def test_find_in_parent_dir(self, tmp_path: Path) -> None:
        """Find config file in parent directory."""
        config_file = tmp_path / DEFAULT_CONFIG_FILE
        config_file.write_text("[app]\n")

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        result = find_config_file(subdir)
        assert result == config_file

    def test_find_in_grandparent_dir(self, tmp_path: Path) -> None:
        """Find config file in grandparent directory."""
        config_file = tmp_path / DEFAULT_CONFIG_FILE
        config_file.write_text("[app]\n")

        subdir = tmp_path / "a" / "b"
        subdir.mkdir(parents=True)

        result = find_config_file(subdir)
        assert result == config_file

    def test_not_found(self, tmp_path: Path) -> None:
        """Return None when no config file found."""
        result = find_config_file(tmp_path)
        assert result is None

    def test_default_to_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Use current working directory when start_dir is None."""
        config_file = tmp_path / DEFAULT_CONFIG_FILE
        config_file.write_text("[app]\n")

        monkeypatch.chdir(tmp_path)
        result = find_config_file(None)
        assert result == config_file


class TestLoadToml:
    """Tests for load_toml function."""

    def test_load_simple_toml(self, tmp_path: Path) -> None:
        """Load simple TOML file."""
        config_file = tmp_path / "test.toml"
        config_file.write_text("""
[app]
debug = true
routes_dir = "api"
""")

        result = load_toml(config_file)
        assert result["app"]["debug"] is True
        assert result["app"]["routes_dir"] == "api"

    def test_load_nested_toml(self, tmp_path: Path) -> None:
        """Load TOML file with nested sections."""
        config_file = tmp_path / "test.toml"
        config_file.write_text("""
[middleware.cors]
enabled = true
allow_origins = ["*"]
""")

        result = load_toml(config_file)
        assert result["middleware"]["cors"]["enabled"] is True
        assert result["middleware"]["cors"]["allow_origins"] == ["*"]


class TestDictToConfig:
    """Tests for dict_to_config function."""

    def test_empty_dict(self) -> None:
        """Empty dict returns default config."""
        result = dict_to_config({})
        assert isinstance(result, PykourConfig)
        assert result.app.debug is False
        assert result.app.routes_dir == "routes"

    def test_app_config(self) -> None:
        """Parse app configuration."""
        data: dict[str, Any] = {
            "app": {
                "debug": True,
                "routes_dir": "api",
            }
        }

        result = dict_to_config(data)
        assert result.app.debug is True
        assert result.app.routes_dir == "api"

    def test_database_config(self) -> None:
        """Parse database configuration."""
        data: dict[str, Any] = {
            "database": {
                "url": "sqlite:///test.db",
                "min_size": 2,
                "max_size": 20,
                "enable_access_policies": False,
            }
        }

        result = dict_to_config(data)
        assert result.database.url == "sqlite:///test.db"
        assert result.database.min_size == 2
        assert result.database.max_size == 20
        assert result.database.enable_access_policies is False

    def test_cache_config(self) -> None:
        """Parse cache configuration."""
        data: dict[str, Any] = {
            "cache": {
                "url": "valkey://localhost",
                "prefix": "myapp:",
            }
        }

        result = dict_to_config(data)
        assert result.cache.url == "valkey://localhost"
        assert result.cache.prefix == "myapp:"

    def test_openapi_config(self) -> None:
        """Parse OpenAPI configuration."""
        data: dict[str, Any] = {
            "openapi": {
                "title": "My API",
                "version": "2.0.0",
                "description": "My API description",
                "docs_url": "/swagger",
                "openapi_url": "/api.json",
                "redoc_url": None,
            }
        }

        result = dict_to_config(data)
        assert result.openapi.title == "My API"
        assert result.openapi.version == "2.0.0"
        assert result.openapi.description == "My API description"
        assert result.openapi.docs_url == "/swagger"
        assert result.openapi.openapi_url == "/api.json"
        assert result.openapi.redoc_url is None

    def test_openapi_contact_config(self) -> None:
        """Parse OpenAPI contact configuration."""
        data: dict[str, Any] = {
            "openapi": {
                "contact": {
                    "name": "Support Team",
                    "url": "https://support.example.com",
                    "email": "support@example.com",
                }
            }
        }

        result = dict_to_config(data)
        assert result.openapi.contact is not None
        assert result.openapi.contact.name == "Support Team"
        assert result.openapi.contact.url == "https://support.example.com"
        assert result.openapi.contact.email == "support@example.com"

    def test_openapi_license_config(self) -> None:
        """Parse OpenAPI license configuration."""
        data: dict[str, Any] = {
            "openapi": {
                "license": {
                    "name": "MIT",
                    "identifier": "MIT",
                    "url": "https://opensource.org/licenses/MIT",
                }
            }
        }

        result = dict_to_config(data)
        assert result.openapi.license is not None
        assert result.openapi.license.name == "MIT"
        assert result.openapi.license.identifier == "MIT"

    def test_openapi_servers_config(self) -> None:
        """Parse OpenAPI servers configuration."""
        data: dict[str, Any] = {
            "openapi": {
                "servers": [
                    {"url": "https://api.example.com", "description": "Production"},
                    {"url": "https://staging.example.com"},
                ]
            }
        }

        result = dict_to_config(data)
        assert len(result.openapi.servers) == 2
        assert result.openapi.servers[0].url == "https://api.example.com"
        assert result.openapi.servers[0].description == "Production"
        assert result.openapi.servers[1].url == "https://staging.example.com"
        assert result.openapi.servers[1].description is None

    def test_health_config(self) -> None:
        """Parse health check configuration."""
        data: dict[str, Any] = {
            "health": {
                "url": "/healthz",
                "include_details": True,
                "version": "1.0.0",
            }
        }

        result = dict_to_config(data)
        assert result.health.url == "/healthz"
        assert result.health.include_details is True
        assert result.health.version == "1.0.0"

    def test_metrics_config(self) -> None:
        """Parse metrics configuration."""
        data: dict[str, Any] = {
            "metrics": {
                "url": "/prometheus",
                "enabled": True,
                "namespace": "myapp",
                "subsystem": "api",
            }
        }

        result = dict_to_config(data)
        assert result.metrics.url == "/prometheus"
        assert result.metrics.enabled is True
        assert result.metrics.namespace == "myapp"
        assert result.metrics.subsystem == "api"

    def test_logging_config(self) -> None:
        """Parse logging configuration."""
        data: dict[str, Any] = {
            "logging": {
                "format": "json",
                "level": "DEBUG",
                "logger_name": "myapp",
                "log_request_headers": True,
                "log_response_headers": True,
            }
        }

        result = dict_to_config(data)
        assert result.logging.format == "json"
        assert result.logging.level == "DEBUG"
        assert result.logging.logger_name == "myapp"
        assert result.logging.log_request_headers is True
        assert result.logging.log_response_headers is True

    def test_cors_middleware_config(self) -> None:
        """Parse CORS middleware configuration."""
        data: dict[str, Any] = {
            "middleware": {
                "cors": {
                    "enabled": True,
                    "allow_origins": ["https://example.com"],
                    "allow_methods": ["GET", "POST"],
                    "allow_headers": ["Authorization"],
                    "allow_credentials": True,
                    "expose_headers": ["X-Custom"],
                    "max_age": 3600,
                }
            }
        }

        result = dict_to_config(data)
        assert result.middleware.cors.enabled is True
        assert result.middleware.cors.allow_origins == ["https://example.com"]
        assert result.middleware.cors.allow_methods == ["GET", "POST"]
        assert result.middleware.cors.allow_credentials is True
        assert result.middleware.cors.max_age == 3600

    def test_jwt_middleware_config(self) -> None:
        """Parse JWT middleware configuration."""
        data: dict[str, Any] = {
            "middleware": {
                "jwt": {
                    "enabled": True,
                    "secret_key": "secret123",
                    "algorithm": "HS512",
                    "exclude_paths": ["/health", "/docs"],
                    "auto_error": False,
                }
            }
        }

        result = dict_to_config(data)
        assert result.middleware.jwt.enabled is True
        assert result.middleware.jwt.secret_key == "secret123"
        assert result.middleware.jwt.algorithm == "HS512"
        assert result.middleware.jwt.exclude_paths == ["/health", "/docs"]
        assert result.middleware.jwt.auto_error is False

    def test_rate_limit_middleware_config(self) -> None:
        """Parse rate limit middleware configuration."""
        data: dict[str, Any] = {
            "middleware": {
                "rate_limit": {
                    "enabled": True,
                    "requests_per_second": 100.0,
                    "burst_size": 50,
                    "exclude_paths": ["/health"],
                    "include_headers": False,
                    "path_configs": {
                        "/api/v1": {
                            "requests_per_second": 10.0,
                            "burst_size": 5,
                        }
                    },
                }
            }
        }

        result = dict_to_config(data)
        assert result.middleware.rate_limit.enabled is True
        assert result.middleware.rate_limit.requests_per_second == 100.0
        assert result.middleware.rate_limit.burst_size == 50
        assert "/api/v1" in result.middleware.rate_limit.path_configs
        path_config = result.middleware.rate_limit.path_configs["/api/v1"]
        assert path_config.requests_per_second == 10.0
        assert path_config.burst_size == 5

    def test_security_middleware_config(self) -> None:
        """Parse security middleware configuration."""
        data: dict[str, Any] = {
            "middleware": {
                "security": {
                    "enabled": True,
                    "hsts_max_age": 86400,
                    "hsts_include_subdomains": False,
                    "x_frame_options": "SAMEORIGIN",
                    "csp": {
                        "default_src": ["'self'"],
                        "script_src": ["'self'", "cdn.example.com"],
                    },
                    "csp_report_only": True,
                }
            }
        }

        result = dict_to_config(data)
        assert result.middleware.security.enabled is True
        assert result.middleware.security.hsts_max_age == 86400
        assert result.middleware.security.hsts_include_subdomains is False
        assert result.middleware.security.x_frame_options == "SAMEORIGIN"
        assert result.middleware.security.csp is not None
        assert result.middleware.security.csp.default_src == ["'self'"]
        assert result.middleware.security.csp.script_src == [
            "'self'",
            "cdn.example.com",
        ]
        assert result.middleware.security.csp_report_only is True

    def test_csrf_middleware_config(self) -> None:
        """Parse CSRF middleware configuration."""
        data: dict[str, Any] = {
            "middleware": {
                "csrf": {
                    "enabled": True,
                    "cookie_name": "my_csrf",
                    "header_name": "X-My-CSRF",
                    "cookie_secure": True,
                    "cookie_httponly": True,
                    "cookie_samesite": "Strict",
                }
            }
        }

        result = dict_to_config(data)
        assert result.middleware.csrf.enabled is True
        assert result.middleware.csrf.cookie_name == "my_csrf"
        assert result.middleware.csrf.header_name == "X-My-CSRF"
        assert result.middleware.csrf.cookie_secure is True
        assert result.middleware.csrf.cookie_httponly is True
        assert result.middleware.csrf.cookie_samesite == "Strict"

    def test_size_limit_middleware_config(self) -> None:
        """Parse size limit middleware configuration."""
        data: dict[str, Any] = {
            "middleware": {
                "size_limit": {
                    "enabled": True,
                    "max_size": 2097152,  # 2MB
                    "max_size_by_content_type": {
                        "image/*": 5242880,  # 5MB
                    },
                    "check_content_length": True,
                    "check_body_size": False,
                }
            }
        }

        result = dict_to_config(data)
        assert result.middleware.size_limit.enabled is True
        assert result.middleware.size_limit.max_size == 2097152
        assert "image/*" in result.middleware.size_limit.max_size_by_content_type
        assert result.middleware.size_limit.check_body_size is False

    def test_logging_middleware_config(self) -> None:
        """Parse logging middleware configuration."""
        data: dict[str, Any] = {
            "middleware": {
                "logging": {
                    "enabled": True,
                    "format": "json",
                    "level": "DEBUG",
                    "exclude_paths": ["/health"],
                }
            }
        }

        result = dict_to_config(data)
        assert result.middleware.logging.enabled is True
        assert result.middleware.logging.format == "json"
        assert result.middleware.logging.level == "DEBUG"

    def test_trace_middleware_config(self) -> None:
        """Parse trace middleware configuration."""
        data: dict[str, Any] = {
            "middleware": {
                "trace": {
                    "enabled": True,
                }
            }
        }

        result = dict_to_config(data)
        assert result.middleware.trace.enabled is True


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_default_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Load default config when no file specified."""
        # Change to temp dir to avoid picking up project's pykour.toml
        monkeypatch.chdir(tmp_path)
        # Clear any env vars that might affect config loading
        monkeypatch.delenv("PYKOUR_CONFIG_FILE", raising=False)
        monkeypatch.delenv("PYKOUR_DEBUG", raising=False)
        config = load_config(auto_discover=False)
        assert isinstance(config, PykourConfig)
        assert config.app.debug is False

    def test_load_from_explicit_file(self, tmp_path: Path) -> None:
        """Load config from explicit file path."""
        config_file = tmp_path / "custom.toml"
        config_file.write_text("""
[app]
debug = true
""")

        config = load_config(config_file=config_file)
        assert config.app.debug is True

    def test_load_from_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Load config from PYKOUR_CONFIG_FILE env var."""
        config_file = tmp_path / "env.toml"
        config_file.write_text("""
[app]
routes_dir = "from_env"
""")

        monkeypatch.setenv("PYKOUR_CONFIG_FILE", str(config_file))
        config = load_config()
        assert config.app.routes_dir == "from_env"

    def test_auto_discover(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Auto-discover pykour.toml in parent directories."""
        config_file = tmp_path / DEFAULT_CONFIG_FILE
        config_file.write_text("""
[app]
debug = true
routes_dir = "discovered"
""")

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        config = load_config(auto_discover=True)
        assert config.app.debug is True
        assert config.app.routes_dir == "discovered"

    def test_explicit_file_not_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Return default config when explicit file doesn't exist."""
        # Change to temp dir to avoid picking up project's pykour.toml
        monkeypatch.chdir(tmp_path)
        # Clear any env vars that might affect config loading
        monkeypatch.delenv("PYKOUR_CONFIG_FILE", raising=False)
        monkeypatch.delenv("PYKOUR_DEBUG", raising=False)
        nonexistent = tmp_path / "nonexistent.toml"
        config = load_config(config_file=nonexistent, auto_discover=False)
        # Should return default config
        assert config.app.debug is False


class TestConfigModels:
    """Tests for configuration dataclasses."""

    def test_app_config_defaults(self) -> None:
        """AppConfig has correct defaults."""
        config = AppConfig()
        assert config.routes_dir == "routes"
        assert config.debug is False

    def test_database_config_defaults(self) -> None:
        """DatabaseConfig has correct defaults."""
        config = DatabaseConfig()
        assert config.url is None
        assert config.min_size == 1
        assert config.max_size == 10
        assert config.enable_access_policies is True

    def test_cache_config_defaults(self) -> None:
        """CacheConfig has correct defaults."""
        config = CacheConfig()
        assert config.url is None
        assert config.prefix == "pykour:"

    def test_openapi_config_defaults(self) -> None:
        """OpenAPIConfigModel has correct defaults."""
        config = OpenAPIConfigModel()
        assert config.title == "Pykour API"
        assert config.version == "1.0.0"
        assert config.description is None
        assert config.docs_url == "/docs"
        assert config.openapi_url == "/openapi.json"
        assert config.redoc_url == "/redoc"
        assert config.contact is None
        assert config.license is None
        assert config.servers == []

    def test_health_config_defaults(self) -> None:
        """HealthConfig has correct defaults."""
        config = HealthConfig()
        assert config.url == "/health"
        assert config.include_details is False
        assert config.version is None

    def test_metrics_config_defaults(self) -> None:
        """MetricsConfigModel has correct defaults."""
        config = MetricsConfigModel()
        assert config.url == "/metrics"
        assert config.enabled is False
        assert config.namespace == ""
        assert config.subsystem == "http"
        assert config.normalize_paths is True

    def test_logging_config_defaults(self) -> None:
        """LoggingConfig has correct defaults."""
        config = LoggingConfig()
        assert config.format == "text"
        assert config.level == "INFO"
        assert config.logger_name == "pykour.access"
        assert config.log_request_headers is False
        assert config.log_response_headers is False

    def test_cors_middleware_defaults(self) -> None:
        """CORSMiddlewareConfig has correct defaults."""
        config = CORSMiddlewareConfig()
        assert config.enabled is False
        assert config.allow_origins == []
        assert config.allow_methods == ["GET"]
        assert config.allow_headers == []
        assert config.allow_credentials is False
        assert config.expose_headers == []
        assert config.max_age == 600

    def test_jwt_middleware_defaults(self) -> None:
        """JWTMiddlewareConfig has correct defaults."""
        config = JWTMiddlewareConfig()
        assert config.enabled is False
        assert config.secret_key is None
        assert config.secret_keys is None
        assert config.algorithm == "HS256"
        assert config.exclude_paths == []
        assert config.auto_error is True

    def test_rate_limit_middleware_defaults(self) -> None:
        """RateLimitMiddlewareConfig has correct defaults."""
        config = RateLimitMiddlewareConfig()
        assert config.enabled is False
        assert config.requests_per_second == 10.0
        assert config.burst_size == 20
        assert config.exclude_paths == []
        assert config.include_headers is True
        assert config.path_configs == {}

    def test_security_middleware_defaults(self) -> None:
        """SecurityMiddlewareConfig has correct defaults."""
        config = SecurityMiddlewareConfig()
        assert config.enabled is False
        assert config.hsts_max_age == 31536000
        assert config.hsts_include_subdomains is True
        assert config.hsts_preload is False
        assert config.x_content_type_options == "nosniff"
        assert config.x_frame_options == "DENY"
        assert config.x_xss_protection == "0"
        assert config.referrer_policy == "strict-origin-when-cross-origin"
        assert config.csp is None
        assert config.csp_report_only is False

    def test_csp_config_defaults(self) -> None:
        """CSPConfig has correct defaults."""
        config = CSPConfig()
        assert config.default_src == ["'self'"]
        assert config.script_src is None
        assert config.style_src is None
        assert config.img_src is None

    def test_csrf_middleware_defaults(self) -> None:
        """CSRFMiddlewareConfig has correct defaults."""
        config = CSRFMiddlewareConfig()
        assert config.enabled is False
        assert config.cookie_name == "csrf_token"
        assert config.header_name == "X-CSRF-Token"
        assert config.cookie_path == "/"
        assert config.cookie_domain is None
        assert config.cookie_secure is False
        assert config.cookie_httponly is False
        assert config.cookie_samesite == "Lax"
        assert config.cookie_max_age == 86400

    def test_size_limit_middleware_defaults(self) -> None:
        """SizeLimitMiddlewareConfig has correct defaults."""
        config = SizeLimitMiddlewareConfig()
        assert config.enabled is False
        assert config.max_size == 1048576  # 1MB
        assert config.max_size_by_content_type == {}
        assert config.check_content_length is True
        assert config.check_body_size is True

    def test_logging_middleware_defaults(self) -> None:
        """LoggingMiddlewareConfig has correct defaults."""
        config = LoggingMiddlewareConfig()
        assert config.enabled is False
        assert config.format == "text"
        assert config.level == "INFO"
        assert config.exclude_paths == []

    def test_trace_middleware_defaults(self) -> None:
        """TraceMiddlewareConfig has correct defaults."""
        config = TraceMiddlewareConfig()
        assert config.enabled is False

    def test_middleware_config_defaults(self) -> None:
        """MiddlewareConfig has correct defaults."""
        config = MiddlewareConfig()
        assert isinstance(config.cors, CORSMiddlewareConfig)
        assert isinstance(config.jwt, JWTMiddlewareConfig)
        assert isinstance(config.rate_limit, RateLimitMiddlewareConfig)
        assert isinstance(config.security, SecurityMiddlewareConfig)
        assert isinstance(config.csrf, CSRFMiddlewareConfig)
        assert isinstance(config.size_limit, SizeLimitMiddlewareConfig)
        assert isinstance(config.logging, LoggingMiddlewareConfig)
        assert isinstance(config.trace, TraceMiddlewareConfig)

    def test_pykour_config_defaults(self) -> None:
        """PykourConfig has correct defaults."""
        config = PykourConfig()
        assert isinstance(config.app, AppConfig)
        assert isinstance(config.openapi, OpenAPIConfigModel)
        assert isinstance(config.health, HealthConfig)
        assert isinstance(config.metrics, MetricsConfigModel)
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.cache, CacheConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.middleware, MiddlewareConfig)


class TestConfigImports:
    """Tests for config module imports."""

    def test_import_from_config_module(self) -> None:
        """Config classes can be imported from pykour.config."""
        from pykour.config import PykourConfig, load_config

        assert PykourConfig is not None
        assert load_config is not None
