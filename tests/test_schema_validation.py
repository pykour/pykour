"""Tests for schema validation."""

import pytest

from pykour import Field, Schema, ValidationError


class UserSchema(Schema):
    """Test user schema."""

    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=0, le=150)
    email: str | None = None


class TestSchemaBasics:
    """Test basic schema functionality."""

    def test_valid_data(self) -> None:
        """Valid data should create schema instance."""
        user = UserSchema(name="Alice", age=30)
        assert user.name == "Alice"
        assert user.age == 30
        assert user.email is None

    def test_all_fields(self) -> None:
        """All fields should be settable."""
        user = UserSchema(name="Bob", age=25, email="bob@example.com")
        assert user.name == "Bob"
        assert user.age == 25
        assert user.email == "bob@example.com"

    def test_model_dump(self) -> None:
        """model_dump should return dict."""
        user = UserSchema(name="Charlie", age=35, email="charlie@example.com")
        result = user.model_dump()
        assert result == {
            "name": "Charlie",
            "age": 35,
            "email": "charlie@example.com",
        }

    def test_repr(self) -> None:
        """repr should show field values."""
        user = UserSchema(name="Dave", age=40)
        assert "Dave" in repr(user)
        assert "40" in repr(user)


class TestSchemaValidation:
    """Test schema validation."""

    def test_missing_required_field(self) -> None:
        """Missing required field should raise ValidationError."""
        with pytest.raises(ValidationError) as exc:
            UserSchema(age=30)

        assert len(exc.value.errors) == 1
        assert exc.value.errors[0].loc == ("body", "name")
        assert exc.value.errors[0].type == "value_error.missing"

    def test_min_length_violation(self) -> None:
        """Violating min_length should raise ValidationError."""
        with pytest.raises(ValidationError) as exc:
            UserSchema(name="", age=30)

        errors = exc.value.errors
        assert len(errors) == 1
        assert errors[0].loc == ("body", "name")
        assert "min" in errors[0].type.lower()

    def test_max_length_violation(self) -> None:
        """Violating max_length should raise ValidationError."""
        with pytest.raises(ValidationError) as exc:
            UserSchema(name="x" * 101, age=30)

        errors = exc.value.errors
        assert len(errors) == 1
        assert errors[0].loc == ("body", "name")

    def test_ge_violation(self) -> None:
        """Violating ge constraint should raise ValidationError."""
        with pytest.raises(ValidationError) as exc:
            UserSchema(name="Test", age=-1)

        errors = exc.value.errors
        assert len(errors) == 1
        assert errors[0].loc == ("body", "age")

    def test_le_violation(self) -> None:
        """Violating le constraint should raise ValidationError."""
        with pytest.raises(ValidationError) as exc:
            UserSchema(name="Test", age=200)

        errors = exc.value.errors
        assert len(errors) == 1
        assert errors[0].loc == ("body", "age")

    def test_multiple_errors(self) -> None:
        """Multiple validation errors should be collected."""
        with pytest.raises(ValidationError) as exc:
            UserSchema(name="", age=-1)

        errors = exc.value.errors
        assert len(errors) == 2

    def test_type_coercion(self) -> None:
        """Types should be coerced."""
        user = UserSchema(name="Test", age="25")
        assert user.age == 25
        assert isinstance(user.age, int)


class TestSchemaWithPattern:
    """Test schema with pattern validation."""

    class EmailSchema(Schema):
        """Schema with email pattern."""

        email: str = Field(pattern=r"^[\w.-]+@[\w.-]+\.\w+$")

    def test_valid_pattern(self) -> None:
        """Valid pattern should pass."""
        schema = self.EmailSchema(email="test@example.com")
        assert schema.email == "test@example.com"

    def test_invalid_pattern(self) -> None:
        """Invalid pattern should raise ValidationError."""
        with pytest.raises(ValidationError) as exc:
            self.EmailSchema(email="not-an-email")

        assert len(exc.value.errors) == 1
        assert "pattern" in exc.value.errors[0].type


class TestSchemaWithDefaultFactory:
    """Test schema with default_factory."""

    class ListSchema(Schema):
        """Schema with list default."""

        items: list[str] = Field(default_factory=list)

    def test_default_factory(self) -> None:
        """default_factory should create new list each time."""
        schema1 = self.ListSchema()
        schema2 = self.ListSchema()
        assert schema1.items == []
        assert schema2.items == []
        assert schema1.items is not schema2.items


class TestSchemaWithAlias:
    """Test schema with alias."""

    class AliasSchema(Schema):
        """Schema with alias."""

        user_name: str = Field(alias="userName")

    def test_alias_works(self) -> None:
        """Alias should map to field."""
        schema = self.AliasSchema(userName="Alice")
        assert schema.user_name == "Alice"


class Address(Schema):
    """Nested address schema."""

    city: str
    country: str = "Japan"


class Person(Schema):
    """Schema with nested address."""

    name: str
    address: Address


class TestNestedSchema:
    """Test nested schema validation."""

    def test_nested_schema(self) -> None:
        """Nested schema should validate."""
        person = Person(
            name="Taro",
            address={"city": "Tokyo"},
        )
        assert person.name == "Taro"
        assert person.address.city == "Tokyo"
        assert person.address.country == "Japan"


class TestValidationErrorFormat:
    """Test ValidationError formatting."""

    def test_to_dict(self) -> None:
        """to_dict should return proper format."""
        with pytest.raises(ValidationError) as exc:
            UserSchema(age=30)  # Missing name

        result = exc.value.to_dict()
        assert result["error"] == "Validation Error"
        assert len(result["detail"]) == 1
        assert result["detail"][0]["loc"] == ["body", "name"]


class TestGtLtValidation:
    """Test gt (greater than) and lt (less than) validators."""

    class ScoreSchema(Schema):
        """Schema with gt/lt constraints."""

        score: int = Field(gt=0, lt=100)  # 0 < score < 100
        temperature: float = Field(gt=-273.15)  # Must be greater than absolute zero

    class IntOnlySchema(Schema):
        """Schema with only gt constraint."""

        value: int = Field(gt=10)

    class FloatOnlySchema(Schema):
        """Schema with only lt constraint."""

        value: float = Field(lt=0.0)

    def test_gt_valid(self) -> None:
        """Value satisfying gt constraint should succeed."""
        schema = self.ScoreSchema(score=50, temperature=20.0)
        assert schema.score == 50
        assert schema.temperature == 20.0

    def test_gt_boundary_invalid(self) -> None:
        """Value equal to gt limit should fail."""
        with pytest.raises(ValidationError) as exc:
            self.ScoreSchema(score=0, temperature=20.0)  # 0 is not > 0

        errors = exc.value.errors
        assert len(errors) == 1
        assert errors[0].loc == ("body", "score")

    def test_gt_below_boundary_invalid(self) -> None:
        """Value below gt limit should fail."""
        with pytest.raises(ValidationError) as exc:
            self.IntOnlySchema(value=5)  # 5 is not > 10

        errors = exc.value.errors
        assert len(errors) == 1

    def test_lt_valid(self) -> None:
        """Value satisfying lt constraint should succeed."""
        schema = self.ScoreSchema(score=99, temperature=20.0)
        assert schema.score == 99

    def test_lt_boundary_invalid(self) -> None:
        """Value equal to lt limit should fail."""
        with pytest.raises(ValidationError) as exc:
            self.ScoreSchema(score=100, temperature=20.0)  # 100 is not < 100

        errors = exc.value.errors
        assert len(errors) == 1
        assert errors[0].loc == ("body", "score")

    def test_lt_above_boundary_invalid(self) -> None:
        """Value above lt limit should fail."""
        with pytest.raises(ValidationError) as exc:
            self.FloatOnlySchema(value=0.5)  # 0.5 is not < 0.0

        errors = exc.value.errors
        assert len(errors) == 1

    def test_gt_lt_combined_valid(self) -> None:
        """Value within gt and lt range should succeed."""
        schema = self.ScoreSchema(score=50, temperature=0.0)
        assert schema.score == 50
        assert schema.temperature == 0.0

    def test_gt_lt_combined_at_boundaries(self) -> None:
        """Values at both boundaries should fail."""
        # Both boundaries fail
        with pytest.raises(ValidationError) as exc:
            self.ScoreSchema(score=0, temperature=-273.15)

        errors = exc.value.errors
        assert len(errors) == 2  # Both score and temperature fail

    def test_float_gt_constraint(self) -> None:
        """Float value satisfying gt constraint should succeed."""
        schema = self.ScoreSchema(score=50, temperature=-273.14)
        assert schema.temperature == -273.14

    def test_float_lt_constraint(self) -> None:
        """Float value satisfying lt constraint should succeed."""
        schema = self.FloatOnlySchema(value=-0.001)
        assert schema.value == -0.001

    def test_gt_with_type_coercion(self) -> None:
        """String coerced to int should validate gt constraint."""
        schema = self.IntOnlySchema(value="15")  # String "15" coerced to int
        assert schema.value == 15
        assert isinstance(schema.value, int)
