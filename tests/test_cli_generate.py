"""Tests for CLI generate command."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pykour.cli.commands.generate import (
    cmd_generate_crud,
    cmd_generate_route,
    register_command,
)
from pykour.generators.route import RouteGenerator, parse_methods


class TestGenerateCommandRegistration:
    """Test generate command registration."""

    def test_register_command_creates_parser(self) -> None:
        """register_command should create the generate parser."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        # Should parse 'generate crud' without error
        args = parser.parse_args(["generate", "crud", "users"])
        assert args.resource == "users"

    def test_generate_requires_subcommand(self) -> None:
        """generate command should require a subcommand."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        # Should fail without subcommand
        with pytest.raises(SystemExit):
            parser.parse_args(["generate"])


class TestCrudGeneratorArguments:
    """Test CRUD generator argument parsing."""

    def test_resource_argument_required(self) -> None:
        """Resource argument should be required."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        with pytest.raises(SystemExit):
            parser.parse_args(["generate", "crud"])

    def test_resource_argument_parsed(self) -> None:
        """Resource argument should be parsed correctly."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "products"])
        assert args.resource == "products"

    def test_table_option(self) -> None:
        """--table should set table_name."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            ["generate", "crud", "users", "--table", "user_accounts"]
        )
        assert args.table_name == "user_accounts"

    def test_table_option_default_none(self) -> None:
        """--table should default to None."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users"])
        assert args.table_name is None

    def test_id_field_option(self) -> None:
        """--id-field should set id_field."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users", "--id-field", "user_id"])
        assert args.id_field == "user_id"

    def test_id_field_default(self) -> None:
        """--id-field should default to 'id'."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users"])
        assert args.id_field == "id"

    def test_id_type_option_int(self) -> None:
        """--id-type should accept 'int'."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users", "--id-type", "int"])
        assert args.id_type == "int"

    def test_id_type_option_str(self) -> None:
        """--id-type should accept 'str'."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users", "--id-type", "str"])
        assert args.id_type == "str"

    def test_id_type_invalid_choice(self) -> None:
        """--id-type should reject invalid choices."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        with pytest.raises(SystemExit):
            parser.parse_args(["generate", "crud", "users", "--id-type", "uuid"])

    def test_id_type_default(self) -> None:
        """--id-type should default to 'int'."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users"])
        assert args.id_type == "int"

    def test_routes_dir_option(self) -> None:
        """--routes-dir should set routes_dir."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            ["generate", "crud", "users", "--routes-dir", "src/routes"]
        )
        assert args.routes_dir == "src/routes"

    def test_routes_dir_default(self) -> None:
        """--routes-dir should default to 'routes'."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users"])
        assert args.routes_dir == "routes"

    def test_with_schema_flag(self) -> None:
        """--with-schema should be a boolean flag."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users", "--with-schema"])
        assert args.with_schema is True

    def test_with_schema_default_false(self) -> None:
        """--with-schema should default to False."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users"])
        assert args.with_schema is False

    def test_with_tests_flag(self) -> None:
        """--with-tests should be a boolean flag."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users", "--with-tests"])
        assert args.with_tests is True

    def test_with_tests_default_false(self) -> None:
        """--with-tests should default to False."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users"])
        assert args.with_tests is False

    def test_force_flag(self) -> None:
        """--force should be a boolean flag."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users", "--force"])
        assert args.force is True

    def test_force_short_flag(self) -> None:
        """-f should be a short form of --force."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users", "-f"])
        assert args.force is True

    def test_force_default_false(self) -> None:
        """--force should default to False."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users"])
        assert args.force is False

    def test_table_class_option(self) -> None:
        """--table-class should set table_class."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            ["generate", "crud", "users", "--table-class", "app.tables:UserTable"]
        )
        assert args.table_class == "app.tables:UserTable"

    def test_table_class_default_none(self) -> None:
        """--table-class should default to None."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users"])
        assert args.table_class is None

    def test_all_options_combined(self) -> None:
        """All options should be parseable together."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            [
                "generate",
                "crud",
                "products",
                "--table",
                "product_items",
                "--id-field",
                "product_id",
                "--id-type",
                "str",
                "--routes-dir",
                "src/routes",
                "--with-schema",
                "--with-tests",
                "--force",
                "--table-class",
                "app.tables:ProductTable",
            ]
        )
        assert args.resource == "products"
        assert args.table_name == "product_items"
        assert args.id_field == "product_id"
        assert args.id_type == "str"
        assert args.routes_dir == "src/routes"
        assert args.with_schema is True
        assert args.with_tests is True
        assert args.force is True
        assert args.table_class == "app.tables:ProductTable"


class TestCrudCommandExecution:
    """Test CRUD command execution."""

    @patch("pykour.generators.crud.CRUDGenerator")
    def test_basic_generation(self, mock_generator_class: MagicMock) -> None:
        """Basic CRUD generation should succeed."""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = [
            Path("routes/api/users/route.py"),
            Path("routes/api/users/[id]/route.py"),
        ]
        mock_generator.resource_singular = "user"
        mock_generator_class.return_value = mock_generator

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users"])
        result = cmd_generate_crud(args)

        assert result == 0
        mock_generator_class.assert_called_once_with(
            resource_name="users",
            table_name=None,
            table_class=None,
            id_field="id",
            id_type="int",
            routes_dir="routes",
        )
        mock_generator.generate.assert_called_once_with(
            with_schema=False,
            with_tests=False,
            force=False,
        )

    @patch("pykour.generators.crud.CRUDGenerator")
    def test_with_schema_option(self, mock_generator_class: MagicMock) -> None:
        """--with-schema should be passed to generator."""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = [
            Path("routes/api/users/route.py"),
            Path("routes/api/users/[id]/route.py"),
            Path("schemas/user.py"),
        ]
        mock_generator.resource_singular = "user"
        mock_generator_class.return_value = mock_generator

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users", "--with-schema"])
        result = cmd_generate_crud(args)

        assert result == 0
        mock_generator.generate.assert_called_once_with(
            with_schema=True,
            with_tests=False,
            force=False,
        )

    @patch("pykour.generators.crud.CRUDGenerator")
    def test_with_tests_option(self, mock_generator_class: MagicMock) -> None:
        """--with-tests should be passed to generator."""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = [
            Path("routes/api/users/route.py"),
            Path("routes/api/users/[id]/route.py"),
            Path("tests/test_users_api.py"),
        ]
        mock_generator.resource_singular = "user"
        mock_generator_class.return_value = mock_generator

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users", "--with-tests"])
        result = cmd_generate_crud(args)

        assert result == 0
        mock_generator.generate.assert_called_once_with(
            with_schema=False,
            with_tests=True,
            force=False,
        )

    @patch("pykour.generators.crud.CRUDGenerator")
    def test_force_option(self, mock_generator_class: MagicMock) -> None:
        """--force should be passed to generator."""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = [
            Path("routes/api/users/route.py"),
            Path("routes/api/users/[id]/route.py"),
        ]
        mock_generator.resource_singular = "user"
        mock_generator_class.return_value = mock_generator

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users", "--force"])
        result = cmd_generate_crud(args)

        assert result == 0
        mock_generator.generate.assert_called_once_with(
            with_schema=False,
            with_tests=False,
            force=True,
        )

    @patch("pykour.generators.crud.CRUDGenerator")
    def test_custom_table_name(self, mock_generator_class: MagicMock) -> None:
        """--table should be passed to generator."""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = [Path("routes/api/users/route.py")]
        mock_generator.resource_singular = "user"
        mock_generator_class.return_value = mock_generator

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            ["generate", "crud", "users", "--table", "user_accounts"]
        )
        cmd_generate_crud(args)

        mock_generator_class.assert_called_once()
        call_kwargs = mock_generator_class.call_args[1]
        assert call_kwargs["table_name"] == "user_accounts"

    @patch("pykour.generators.crud.CRUDGenerator")
    def test_custom_id_field(self, mock_generator_class: MagicMock) -> None:
        """--id-field should be passed to generator."""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = [Path("routes/api/users/route.py")]
        mock_generator.resource_singular = "user"
        mock_generator_class.return_value = mock_generator

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users", "--id-field", "user_id"])
        cmd_generate_crud(args)

        mock_generator_class.assert_called_once()
        call_kwargs = mock_generator_class.call_args[1]
        assert call_kwargs["id_field"] == "user_id"

    @patch("pykour.generators.crud.CRUDGenerator")
    def test_custom_id_type(self, mock_generator_class: MagicMock) -> None:
        """--id-type should be passed to generator."""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = [Path("routes/api/users/route.py")]
        mock_generator.resource_singular = "user"
        mock_generator_class.return_value = mock_generator

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users", "--id-type", "str"])
        cmd_generate_crud(args)

        mock_generator_class.assert_called_once()
        call_kwargs = mock_generator_class.call_args[1]
        assert call_kwargs["id_type"] == "str"

    @patch("pykour.generators.crud.CRUDGenerator")
    def test_custom_routes_dir(self, mock_generator_class: MagicMock) -> None:
        """--routes-dir should be passed to generator."""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = [Path("src/routes/api/users/route.py")]
        mock_generator.resource_singular = "user"
        mock_generator_class.return_value = mock_generator

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            ["generate", "crud", "users", "--routes-dir", "src/routes"]
        )
        cmd_generate_crud(args)

        mock_generator_class.assert_called_once()
        call_kwargs = mock_generator_class.call_args[1]
        assert call_kwargs["routes_dir"] == "src/routes"


class TestCrudCommandTableClass:
    """Test CRUD command with --table-class option."""

    def test_table_class_parsing(self) -> None:
        """--table-class format should be validated."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        # Valid format with colon
        args = parser.parse_args(
            ["generate", "crud", "users", "--table-class", "app.tables:UserTable"]
        )
        assert args.table_class == "app.tables:UserTable"

    def test_table_class_split_format(self) -> None:
        """--table-class value should have module:class format."""
        # The generate command expects module_path:class_name format
        # This is validated at runtime in cmd_generate_crud
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            ["generate", "crud", "users", "--table-class", "myapp.models:Product"]
        )
        assert ":" in args.table_class
        module_path, class_name = args.table_class.rsplit(":", 1)
        assert module_path == "myapp.models"
        assert class_name == "Product"


class TestCrudCommandErrorHandling:
    """Test CRUD command error handling."""

    @patch("pykour.generators.crud.CRUDGenerator")
    def test_file_exists_error(self, mock_generator_class: MagicMock) -> None:
        """FileExistsError should return error code 1."""
        mock_generator = MagicMock()
        mock_generator.generate.side_effect = FileExistsError(
            "File already exists: routes/api/users/route.py"
        )
        mock_generator_class.return_value = mock_generator

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users"])
        result = cmd_generate_crud(args)

        assert result == 1

    def test_invalid_table_class_format_no_colon(self) -> None:
        """Invalid --table-class format (no colon) should return error code 1."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            ["generate", "crud", "users", "--table-class", "app.tables.UserTable"]
        )
        result = cmd_generate_crud(args)

        assert result == 1

    @patch("importlib.import_module")
    def test_import_error(self, mock_import: MagicMock) -> None:
        """ImportError should return error code 1."""
        mock_import.side_effect = ImportError("No module named 'app.tables'")

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            ["generate", "crud", "users", "--table-class", "app.tables:UserTable"]
        )
        result = cmd_generate_crud(args)

        assert result == 1

    @patch("importlib.import_module")
    def test_attribute_error(self, mock_import: MagicMock) -> None:
        """AttributeError should return error code 1."""
        mock_module = MagicMock(spec=[])  # Empty spec, no attributes
        mock_import.return_value = mock_module
        # Make attribute access raise AttributeError
        del mock_module.UserTable

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            ["generate", "crud", "users", "--table-class", "app.tables:UserTable"]
        )
        result = cmd_generate_crud(args)

        assert result == 1

    @patch("pykour.generators.crud.CRUDGenerator")
    def test_generic_exception(self, mock_generator_class: MagicMock) -> None:
        """Generic exception should return error code 1."""
        mock_generator_class.side_effect = RuntimeError("Something went wrong")

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users"])
        result = cmd_generate_crud(args)

        assert result == 1

    @patch("pykour.generators.crud.CRUDGenerator")
    def test_value_error(self, mock_generator_class: MagicMock) -> None:
        """ValueError should return error code 1."""
        mock_generator_class.side_effect = ValueError("Invalid resource name")

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "crud", "users"])
        result = cmd_generate_crud(args)

        assert result == 1


class TestGenerateAliases:
    """Test generate command aliases."""

    def test_generate_alias_gen(self) -> None:
        """'gen' should be an alias for 'generate'."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["gen", "route", "GET", "/api/hello"])
        assert args.method == "GET"
        assert args.path == "/api/hello"

    def test_generate_alias_g(self) -> None:
        """'g' should be an alias for 'generate'."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["g", "route", "GET", "/api/hello"])
        assert args.method == "GET"
        assert args.path == "/api/hello"


class TestParseMethods:
    """Test parse_methods function."""

    def test_single_method(self) -> None:
        """Single method should be parsed."""
        assert parse_methods("GET") == ["GET"]
        assert parse_methods("post") == ["POST"]
        assert parse_methods("Put") == ["PUT"]

    def test_multiple_methods_comma_separated(self) -> None:
        """Comma-separated methods should be parsed."""
        assert parse_methods("GET,POST") == ["GET", "POST"]
        assert parse_methods("get, post, put") == ["GET", "POST", "PUT"]

    def test_crud_expands(self) -> None:
        """CRUD should expand to GET,POST,PUT,DELETE."""
        assert parse_methods("CRUD") == ["GET", "POST", "PUT", "DELETE"]
        assert parse_methods("crud") == ["GET", "POST", "PUT", "DELETE"]

    def test_invalid_method_raises(self) -> None:
        """Invalid method should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid HTTP method"):
            parse_methods("INVALID")

        with pytest.raises(ValueError, match="Invalid HTTP method"):
            parse_methods("GET,INVALID")


class TestRouteGeneratorArguments:
    """Test route generator argument parsing."""

    def test_method_argument_required(self) -> None:
        """Method argument should be required."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        with pytest.raises(SystemExit):
            parser.parse_args(["generate", "route"])

    def test_path_argument_required(self) -> None:
        """Path argument should be required."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        with pytest.raises(SystemExit):
            parser.parse_args(["generate", "route", "GET"])

    def test_arguments_parsed(self) -> None:
        """Method and path arguments should be parsed correctly."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "route", "GET", "/api/v1/hello"])
        assert args.method == "GET"
        assert args.path == "/api/v1/hello"

    def test_routes_dir_option(self) -> None:
        """--routes-dir should set routes_dir."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            ["generate", "route", "GET", "/api/hello", "--routes-dir", "src/routes"]
        )
        assert args.routes_dir == "src/routes"

    def test_routes_dir_default(self) -> None:
        """--routes-dir should default to 'routes'."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "route", "GET", "/api/hello"])
        assert args.routes_dir == "routes"

    def test_force_flag(self) -> None:
        """--force should be a boolean flag."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "route", "GET", "/api/hello", "--force"])
        assert args.force is True

    def test_force_short_flag(self) -> None:
        """-f should be a short form of --force."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "route", "GET", "/api/hello", "-f"])
        assert args.force is True


class TestRouteGenerator:
    """Test RouteGenerator class."""

    def test_path_to_route_dir_simple(self, tmp_path: Path) -> None:
        """Simple path should be converted correctly."""
        generator = RouteGenerator(
            path="/api/v1/hello",
            methods=["GET"],
            routes_dir=str(tmp_path / "routes"),
        )
        route_dir = generator._path_to_route_dir()
        assert route_dir == tmp_path / "routes" / "api" / "v1" / "hello"

    def test_path_to_route_dir_dynamic_param(self, tmp_path: Path) -> None:
        """Path with {param} should be converted to [param]."""
        generator = RouteGenerator(
            path="/api/users/{id}",
            methods=["GET"],
            routes_dir=str(tmp_path / "routes"),
        )
        route_dir = generator._path_to_route_dir()
        assert route_dir == tmp_path / "routes" / "api" / "users" / "[id]"

    def test_generate_creates_file(self, tmp_path: Path) -> None:
        """generate should create route.py file."""
        generator = RouteGenerator(
            path="/api/hello",
            methods=["GET"],
            routes_dir=str(tmp_path / "routes"),
        )
        created_file = generator.generate()

        assert created_file.exists()
        assert created_file.name == "route.py"
        assert created_file.parent == tmp_path / "routes" / "api" / "hello"

    def test_generate_content_single_method(self, tmp_path: Path) -> None:
        """Generated file should contain single handler."""
        generator = RouteGenerator(
            path="/api/hello",
            methods=["GET"],
            routes_dir=str(tmp_path / "routes"),
        )
        created_file = generator.generate()
        content = created_file.read_text()

        assert "async def get(request: Request)" in content
        assert "GET /api/hello" in content
        assert "from pykour import JSONResponse, Request" in content

    def test_generate_content_multiple_methods(self, tmp_path: Path) -> None:
        """Generated file should contain multiple handlers."""
        generator = RouteGenerator(
            path="/api/users",
            methods=["GET", "POST"],
            routes_dir=str(tmp_path / "routes"),
        )
        created_file = generator.generate()
        content = created_file.read_text()

        assert "async def get(request: Request)" in content
        assert "async def post(request: Request)" in content

    def test_generate_content_crud(self, tmp_path: Path) -> None:
        """CRUD should generate all handlers."""
        generator = RouteGenerator(
            path="/api/products",
            methods=["GET", "POST", "PUT", "DELETE"],
            routes_dir=str(tmp_path / "routes"),
        )
        created_file = generator.generate()
        content = created_file.read_text()

        assert "async def get(request: Request)" in content
        assert "async def post(request: Request)" in content
        assert "async def put(request: Request)" in content
        assert "async def delete(request: Request)" in content

    def test_generate_file_exists_error(self, tmp_path: Path) -> None:
        """Existing file should raise FileExistsError."""
        routes_dir = tmp_path / "routes"
        route_dir = routes_dir / "api" / "hello"
        route_dir.mkdir(parents=True)
        (route_dir / "route.py").write_text("# existing")

        generator = RouteGenerator(
            path="/api/hello",
            methods=["GET"],
            routes_dir=str(routes_dir),
        )

        with pytest.raises(FileExistsError):
            generator.generate()

    def test_generate_force_overwrites(self, tmp_path: Path) -> None:
        """--force should overwrite existing file."""
        routes_dir = tmp_path / "routes"
        route_dir = routes_dir / "api" / "hello"
        route_dir.mkdir(parents=True)
        (route_dir / "route.py").write_text("# existing")

        generator = RouteGenerator(
            path="/api/hello",
            methods=["GET"],
            routes_dir=str(routes_dir),
        )
        created_file = generator.generate(force=True)

        content = created_file.read_text()
        assert "# existing" not in content
        assert "async def get" in content


class TestRouteCommandExecution:
    """Test route command execution."""

    @patch("pykour.generators.route.RouteGenerator")
    def test_basic_generation(self, mock_generator_class: MagicMock) -> None:
        """Basic route generation should succeed."""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = Path("routes/api/hello/route.py")
        mock_generator_class.return_value = mock_generator

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "route", "GET", "/api/hello"])
        result = cmd_generate_route(args)

        assert result == 0
        mock_generator_class.assert_called_once_with(
            path="/api/hello",
            methods=["GET"],
            routes_dir="routes",
        )
        mock_generator.generate.assert_called_once_with(force=False)

    @patch("pykour.generators.route.RouteGenerator")
    def test_multiple_methods(self, mock_generator_class: MagicMock) -> None:
        """Multiple methods should be passed to generator."""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = Path("routes/api/users/route.py")
        mock_generator_class.return_value = mock_generator

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "route", "GET,POST", "/api/users"])
        result = cmd_generate_route(args)

        assert result == 0
        mock_generator_class.assert_called_once_with(
            path="/api/users",
            methods=["GET", "POST"],
            routes_dir="routes",
        )

    @patch("pykour.generators.route.RouteGenerator")
    def test_crud_expansion(self, mock_generator_class: MagicMock) -> None:
        """CRUD should expand to all methods."""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = Path("routes/api/products/route.py")
        mock_generator_class.return_value = mock_generator

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "route", "CRUD", "/api/products"])
        result = cmd_generate_route(args)

        assert result == 0
        mock_generator_class.assert_called_once_with(
            path="/api/products",
            methods=["GET", "POST", "PUT", "DELETE"],
            routes_dir="routes",
        )

    @patch("pykour.generators.route.RouteGenerator")
    def test_force_option(self, mock_generator_class: MagicMock) -> None:
        """--force should be passed to generator."""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = Path("routes/api/hello/route.py")
        mock_generator_class.return_value = mock_generator

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "route", "GET", "/api/hello", "--force"])
        result = cmd_generate_route(args)

        assert result == 0
        mock_generator.generate.assert_called_once_with(force=True)

    @patch("pykour.generators.route.RouteGenerator")
    def test_custom_routes_dir(self, mock_generator_class: MagicMock) -> None:
        """--routes-dir should be passed to generator."""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = Path("src/routes/api/hello/route.py")
        mock_generator_class.return_value = mock_generator

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            ["generate", "route", "GET", "/api/hello", "--routes-dir", "src/routes"]
        )
        cmd_generate_route(args)

        mock_generator_class.assert_called_once_with(
            path="/api/hello",
            methods=["GET"],
            routes_dir="src/routes",
        )


class TestRouteCommandErrorHandling:
    """Test route command error handling."""

    @patch("pykour.generators.route.RouteGenerator")
    def test_file_exists_error(self, mock_generator_class: MagicMock) -> None:
        """FileExistsError should return error code 1."""
        mock_generator = MagicMock()
        mock_generator.generate.side_effect = FileExistsError(
            "File already exists: routes/api/hello/route.py"
        )
        mock_generator_class.return_value = mock_generator

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "route", "GET", "/api/hello"])
        result = cmd_generate_route(args)

        assert result == 1

    def test_invalid_method_error(self) -> None:
        """Invalid method should return error code 1."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "route", "INVALID", "/api/hello"])
        result = cmd_generate_route(args)

        assert result == 1

    @patch("pykour.generators.route.RouteGenerator")
    def test_generic_exception(self, mock_generator_class: MagicMock) -> None:
        """Generic exception should return error code 1."""
        mock_generator_class.side_effect = RuntimeError("Something went wrong")

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["generate", "route", "GET", "/api/hello"])
        result = cmd_generate_route(args)

        assert result == 1
