"""Tests for CRUD scaffold code generation."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from pykour.generators.crud import CRUDGenerator
from pykour.generators.naming import (
    camel_to_snake,
    pluralize,
    singularize,
    snake_to_camel,
    snake_to_pascal,
)


class TestPluralizeFunction:
    """Tests for pluralize function."""

    def test_regular_words(self) -> None:
        """Regular words add 's'."""
        assert pluralize("user") == "users"
        assert pluralize("product") == "products"
        assert pluralize("item") == "items"

    def test_words_ending_in_s(self) -> None:
        """Words ending in s/x/z/ch/sh add 'es'."""
        assert pluralize("bus") == "buses"
        assert pluralize("box") == "boxes"
        assert pluralize("buzz") == "buzzes"
        assert pluralize("watch") == "watches"
        assert pluralize("dish") == "dishes"

    def test_words_ending_in_y(self) -> None:
        """Words ending in consonant + y change to 'ies'."""
        assert pluralize("category") == "categories"
        assert pluralize("city") == "cities"
        # Vowel + y just adds 's'
        assert pluralize("day") == "days"
        assert pluralize("key") == "keys"

    def test_words_ending_in_f(self) -> None:
        """Words ending in f change to 'ves'."""
        assert pluralize("leaf") == "leaves"
        assert pluralize("shelf") == "shelves"

    def test_words_ending_in_o(self) -> None:
        """Words ending in consonant + o add 'es'."""
        assert pluralize("hero") == "heroes"
        assert pluralize("potato") == "potatoes"

    def test_irregular_plurals(self) -> None:
        """Irregular plurals are handled."""
        assert pluralize("person") == "people"
        assert pluralize("child") == "children"
        assert pluralize("man") == "men"

    def test_uncountable_words(self) -> None:
        """Uncountable words stay the same."""
        assert pluralize("sheep") == "sheep"
        assert pluralize("fish") == "fish"
        assert pluralize("data") == "data"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert pluralize("") == ""


class TestSingularizeFunction:
    """Tests for singularize function."""

    def test_regular_words(self) -> None:
        """Regular words remove 's'."""
        assert singularize("users") == "user"
        assert singularize("products") == "product"

    def test_words_ending_in_es(self) -> None:
        """Words ending in 'es' remove 'es' or 's' appropriately."""
        assert singularize("buses") == "bus"
        assert singularize("boxes") == "box"
        assert singularize("watches") == "watch"

    def test_words_ending_in_ies(self) -> None:
        """Words ending in 'ies' change to 'y'."""
        assert singularize("categories") == "category"
        assert singularize("cities") == "city"

    def test_irregular_singulars(self) -> None:
        """Irregular singulars are handled."""
        assert singularize("people") == "person"
        assert singularize("children") == "child"
        assert singularize("men") == "man"

    def test_uncountable_words(self) -> None:
        """Uncountable words stay the same."""
        assert singularize("sheep") == "sheep"
        assert singularize("fish") == "fish"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert singularize("") == ""


class TestSnakeToCamel:
    """Tests for snake_to_camel function."""

    def test_basic_conversion(self) -> None:
        """Basic snake_case to camelCase."""
        assert snake_to_camel("user_name") == "userName"
        assert snake_to_camel("get_user_by_id") == "getUserById"

    def test_single_word(self) -> None:
        """Single word stays lowercase."""
        assert snake_to_camel("user") == "user"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert snake_to_camel("") == ""


class TestSnakeToPascal:
    """Tests for snake_to_pascal function."""

    def test_basic_conversion(self) -> None:
        """Basic snake_case to PascalCase."""
        assert snake_to_pascal("user_name") == "UserName"
        assert snake_to_pascal("user_table") == "UserTable"

    def test_single_word(self) -> None:
        """Single word is capitalized."""
        assert snake_to_pascal("user") == "User"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert snake_to_pascal("") == ""


class TestCamelToSnake:
    """Tests for camel_to_snake function."""

    def test_basic_conversion(self) -> None:
        """Basic camelCase/PascalCase to snake_case."""
        assert camel_to_snake("userName") == "user_name"
        assert camel_to_snake("UserTable") == "user_table"
        assert camel_to_snake("getUserById") == "get_user_by_id"

    def test_single_word(self) -> None:
        """Single word is lowercased."""
        assert camel_to_snake("user") == "user"
        assert camel_to_snake("User") == "user"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert camel_to_snake("") == ""


class TestCRUDGenerator:
    """Tests for CRUDGenerator class."""

    def test_init_basic(self) -> None:
        """Basic initialization."""
        gen = CRUDGenerator("users")
        assert gen.resource_name == "users"
        assert gen.resource_plural == "users"
        assert gen.resource_singular == "user"
        assert gen.resource_pascal == "User"
        assert gen.table_name == "users"

    def test_init_singular_input(self) -> None:
        """Singular input is handled."""
        gen = CRUDGenerator("user")
        assert gen.resource_plural == "users"
        assert gen.resource_singular == "user"

    def test_init_custom_table_name(self) -> None:
        """Custom table name is used."""
        gen = CRUDGenerator("users", table_name="user_accounts")
        assert gen.table_name == "user_accounts"

    def test_init_custom_id_field(self) -> None:
        """Custom ID field is used."""
        gen = CRUDGenerator("users", id_field="user_id")
        assert gen.id_field == "user_id"

    def test_init_id_type(self) -> None:
        """ID type is stored."""
        gen = CRUDGenerator("users", id_type="str")
        assert gen.id_type == "str"

    def test_generate_creates_route_files(self) -> None:
        """Generate creates route files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = CRUDGenerator("products", routes_dir=tmpdir)
            files = gen.generate()

            assert len(files) == 2

            # Check collection route
            collection_route = Path(tmpdir) / "api" / "products" / "route.py"
            assert collection_route.exists()
            content = collection_route.read_text()
            assert "async def get(" in content
            assert "async def post(" in content
            assert '"products"' in content

            # Check item route
            item_route = Path(tmpdir) / "api" / "products" / "[id]" / "route.py"
            assert item_route.exists()
            content = item_route.read_text()
            assert "async def get(" in content
            assert "async def put(" in content
            assert "async def delete(" in content

    def test_generate_with_schema(self) -> None:
        """Generate with --with-schema creates schema file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import os

            os.chdir(tmpdir)
            gen = CRUDGenerator("users", routes_dir=tmpdir)
            files = gen.generate(with_schema=True)

            assert len(files) == 3

            schema_file = Path(tmpdir).parent / "schemas" / "user.py"
            # Schema file is created in working directory
            schema_file = Path("schemas") / "user.py"
            assert schema_file.exists()
            content = schema_file.read_text()
            assert "class CreateUserSchema" in content
            assert "class UpdateUserSchema" in content

    def test_generate_with_tests(self) -> None:
        """Generate with --with-tests creates test file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import os

            os.chdir(tmpdir)
            gen = CRUDGenerator("orders", routes_dir=tmpdir)
            files = gen.generate(with_tests=True)

            assert len(files) == 3

            test_file = Path("tests") / "test_orders_api.py"
            assert test_file.exists()
            content = test_file.read_text()
            assert "class TestOrderAPI" in content
            assert "test_list_orders" in content
            assert "test_create_order" in content

    def test_generate_raises_on_existing_file(self) -> None:
        """Generate raises FileExistsError if file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create the route directory and file first
            route_dir = Path(tmpdir) / "api" / "items"
            route_dir.mkdir(parents=True)
            route_file = route_dir / "route.py"
            route_file.write_text("# existing file")

            gen = CRUDGenerator("items", routes_dir=tmpdir)
            with pytest.raises(FileExistsError):
                gen.generate()

    def test_generate_force_overwrites(self) -> None:
        """Generate with force=True overwrites existing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create the route directory and file first
            route_dir = Path(tmpdir) / "api" / "items"
            route_dir.mkdir(parents=True)
            route_file = route_dir / "route.py"
            route_file.write_text("# existing file")

            gen = CRUDGenerator("items", routes_dir=tmpdir)
            files = gen.generate(force=True)

            assert len(files) == 2
            content = route_file.read_text()
            assert "async def get(" in content

    def test_generate_schema_import_in_route(self) -> None:
        """Schema import is added when with_schema is True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import os

            os.chdir(tmpdir)
            gen = CRUDGenerator("users", routes_dir=tmpdir)
            gen.generate(with_schema=True)

            collection_route = Path(tmpdir) / "api" / "users" / "route.py"
            content = collection_route.read_text()
            assert "from schemas.user import CreateUserSchema" in content

            item_route = Path(tmpdir) / "api" / "users" / "[id]" / "route.py"
            content = item_route.read_text()
            assert "from schemas.user import UpdateUserSchema" in content

    def test_generate_no_schema_import_without_flag(self) -> None:
        """No schema import when with_schema is False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = CRUDGenerator("users", routes_dir=tmpdir)
            gen.generate(with_schema=False)

            collection_route = Path(tmpdir) / "api" / "users" / "route.py"
            content = collection_route.read_text()
            assert "from schemas" not in content
            # Uses dict instead of schema
            assert "data: dict = Body()" in content


class TestCRUDGeneratorEdgeCases:
    """Edge case tests for CRUDGenerator."""

    def test_uppercase_resource_name(self) -> None:
        """Uppercase resource name is normalized."""
        gen = CRUDGenerator("USERS")
        assert gen.resource_name == "users"
        assert gen.resource_plural == "users"

    def test_mixed_case_resource_name(self) -> None:
        """Mixed case resource name is normalized."""
        gen = CRUDGenerator("UserProfiles")
        assert gen.resource_name == "userprofiles"

    def test_irregular_plural_resource(self) -> None:
        """Irregular plural resource is handled."""
        gen = CRUDGenerator("people")
        assert gen.resource_plural == "people"
        assert gen.resource_singular == "person"
        assert gen.resource_pascal == "Person"

    def test_category_resource(self) -> None:
        """Category resource pluralization."""
        gen = CRUDGenerator("category")
        assert gen.resource_plural == "categories"
        assert gen.resource_singular == "category"
