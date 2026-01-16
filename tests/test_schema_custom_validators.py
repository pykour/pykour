"""Tests for custom validators (field_validator and model_validator)."""

import pytest

from pykour.schema import Schema, ValidationError, field_validator, model_validator


class TestFieldValidator:
    """Tests for field_validator decorator."""

    def test_field_validator_after_coercion(self) -> None:
        """Field validator should run after type coercion by default."""

        class UserSchema(Schema):
            name: str
            email: str

            @field_validator("name")
            @classmethod
            def validate_name(cls, v: str) -> str:
                return v.strip().title()

            @field_validator("email")
            @classmethod
            def validate_email(cls, v: str) -> str:
                return v.lower()

        user = UserSchema(name="  john doe  ", email="JOHN@EXAMPLE.COM")
        assert user.name == "John Doe"
        assert user.email == "john@example.com"

    def test_field_validator_raises_error(self) -> None:
        """Field validator should be able to raise validation errors."""

        class UserSchema(Schema):
            email: str

            @field_validator("email")
            @classmethod
            def validate_email(cls, v: str) -> str:
                if "@" not in v:
                    raise ValueError("Invalid email format")
                return v

        with pytest.raises(ValidationError) as exc_info:
            UserSchema(email="invalid-email")

        errors = exc_info.value.errors
        assert len(errors) == 1
        assert "Invalid email format" in errors[0].msg

    def test_field_validator_before_coercion(self) -> None:
        """Before validator should run on raw value."""

        class NumSchema(Schema):
            value: int

            @field_validator("value", mode="before")
            @classmethod
            def strip_string(cls, v: str) -> str:
                if isinstance(v, str):
                    return v.strip()
                return v

        # Should work with whitespace around number string
        num = NumSchema(value="  42  ")
        assert num.value == 42

    def test_multiple_validators_same_field(self) -> None:
        """Multiple validators can be applied to the same field."""

        class TextSchema(Schema):
            text: str

            @field_validator("text")
            @classmethod
            def strip_text(cls, v: str) -> str:
                return v.strip()

            @field_validator("text")
            @classmethod
            def uppercase_text(cls, v: str) -> str:
                return v.upper()

        # Validators run in order they are defined
        text = TextSchema(text="  hello world  ")
        # Strip runs first, then uppercase
        assert text.text == "HELLO WORLD"

    def test_validator_for_multiple_fields(self) -> None:
        """Single validator can apply to multiple fields."""

        class FormSchema(Schema):
            first_name: str
            last_name: str

            @field_validator("first_name", "last_name")
            @classmethod
            def strip_and_title(cls, v: str) -> str:
                return v.strip().title()

        form = FormSchema(first_name="  john  ", last_name="  doe  ")
        assert form.first_name == "John"
        assert form.last_name == "Doe"


class TestModelValidator:
    """Tests for model_validator decorator."""

    def test_model_validator_after(self) -> None:
        """After model validator receives the model instance."""

        class PasswordSchema(Schema):
            password: str
            password_confirm: str

            @model_validator(mode="after")
            @classmethod
            def passwords_match(cls, model: "PasswordSchema") -> "PasswordSchema":
                if model.password != model.password_confirm:
                    raise ValueError("Passwords do not match")
                return model

        # Should pass when passwords match
        schema = PasswordSchema(password="secret123", password_confirm="secret123")
        assert schema.password == "secret123"

        # Should fail when passwords don't match
        with pytest.raises(ValidationError) as exc_info:
            PasswordSchema(password="secret123", password_confirm="different")

        errors = exc_info.value.errors
        assert len(errors) == 1
        assert "Passwords do not match" in errors[0].msg

    def test_model_validator_before(self) -> None:
        """Before model validator receives raw data dict."""

        class UserSchema(Schema):
            username: str
            email: str

            @model_validator(mode="before")
            @classmethod
            def preprocess(cls, data: dict) -> dict:
                if "username" in data:
                    data["username"] = data["username"].lower()
                return data

        user = UserSchema(username="JohnDoe", email="john@example.com")
        assert user.username == "johndoe"

    def test_model_validator_transform_data(self) -> None:
        """Model validator can transform data before validation."""

        class AliasSchema(Schema):
            name: str

            @model_validator(mode="before")
            @classmethod
            def handle_alias(cls, data: dict) -> dict:
                # Support both 'name' and 'full_name' as input
                if "full_name" in data and "name" not in data:
                    data["name"] = data["full_name"]
                return data

        # Using standard field
        schema1 = AliasSchema(name="John")
        assert schema1.name == "John"

        # Using alias
        schema2 = AliasSchema(full_name="Jane")
        assert schema2.name == "Jane"


class TestCombinedValidators:
    """Tests for combining field and model validators."""

    def test_field_and_model_validators(self) -> None:
        """Field and model validators should work together."""

        class SignupSchema(Schema):
            email: str
            password: str
            password_confirm: str

            @field_validator("email")
            @classmethod
            def normalize_email(cls, v: str) -> str:
                return v.lower().strip()

            @field_validator("password")
            @classmethod
            def validate_password(cls, v: str) -> str:
                if len(v) < 8:
                    raise ValueError("Password must be at least 8 characters")
                return v

            @model_validator(mode="after")
            @classmethod
            def passwords_match(cls, model: "SignupSchema") -> "SignupSchema":
                if model.password != model.password_confirm:
                    raise ValueError("Passwords do not match")
                return model

        # Valid signup
        signup = SignupSchema(
            email="  USER@EXAMPLE.COM  ",
            password="secret123",
            password_confirm="secret123",
        )
        assert signup.email == "user@example.com"
        assert signup.password == "secret123"

    def test_validation_order(self) -> None:
        """Validators should run in correct order."""
        order: list[str] = []

        class OrderSchema(Schema):
            value: str

            @model_validator(mode="before")
            @classmethod
            def before_model(cls, data: dict) -> dict:
                order.append("before_model")
                return data

            @field_validator("value", mode="before")
            @classmethod
            def before_field(cls, v: str) -> str:
                order.append("before_field")
                return v

            @field_validator("value", mode="after")
            @classmethod
            def after_field(cls, v: str) -> str:
                order.append("after_field")
                return v

            @model_validator(mode="after")
            @classmethod
            def after_model(cls, model: "OrderSchema") -> "OrderSchema":
                order.append("after_model")
                return model

        OrderSchema(value="test")

        assert order == [
            "before_model",
            "before_field",
            "after_field",
            "after_model",
        ]


class TestValidatorEdgeCases:
    """Edge case tests for validators."""

    def test_validator_with_optional_field(self) -> None:
        """Validators should handle optional fields."""
        from typing import Optional

        class OptionalSchema(Schema):
            name: Optional[str] = None

            @field_validator("name")
            @classmethod
            def validate_name(cls, v: str) -> str:
                return v.upper()

        # With value
        schema1 = OptionalSchema(name="john")
        assert schema1.name == "JOHN"

        # Without value (None)
        schema2 = OptionalSchema()
        assert schema2.name is None

    def test_validator_error_message(self) -> None:
        """Validator error should have proper location."""

        class TestSchema(Schema):
            field1: str

            @field_validator("field1")
            @classmethod
            def validate_field1(cls, v: str) -> str:
                if v == "bad":
                    raise ValueError("Field1 cannot be 'bad'")
                return v

        with pytest.raises(ValidationError) as exc_info:
            TestSchema(field1="bad")

        errors = exc_info.value.errors
        assert errors[0].loc == ("body", "field1")
        assert errors[0].type == "value_error.field_validator"

    def test_field_validator_no_fields_error(self) -> None:
        """field_validator without fields should raise error."""
        with pytest.raises(ValueError, match="At least one field name"):

            @field_validator()
            def bad_validator(cls, v):
                return v

    def test_before_validator_failure_skips_type_coercion(self) -> None:
        """When before validator fails, type coercion should be skipped.

        This prevents confusing additional error messages from type coercion
        when the raw value was already rejected by a before validator.
        """

        class StrictIntSchema(Schema):
            value: int

            @field_validator("value", mode="before")
            @classmethod
            def reject_negative_strings(cls, v: str) -> str:
                if isinstance(v, str) and v.startswith("-"):
                    raise ValueError("Negative values not allowed")
                return v

        with pytest.raises(ValidationError) as exc_info:
            StrictIntSchema(value="-42")

        errors = exc_info.value.errors
        # Should only have one error from the before validator,
        # not additional errors from type coercion
        assert len(errors) == 1
        assert "Negative values not allowed" in errors[0].msg
        assert errors[0].type == "value_error.field_validator"

    def test_before_validator_failure_stops_subsequent_validators(self) -> None:
        """When before validator fails, subsequent before validators should not run."""
        validator_calls: list[str] = []

        class MultiValidatorSchema(Schema):
            value: str

            @field_validator("value", mode="before")
            @classmethod
            def first_validator(cls, v: str) -> str:
                validator_calls.append("first")
                if v == "fail":
                    raise ValueError("First validator failed")
                return v

            @field_validator("value", mode="before")
            @classmethod
            def second_validator(cls, v: str) -> str:
                validator_calls.append("second")
                return v

        with pytest.raises(ValidationError):
            MultiValidatorSchema(value="fail")

        # Only the first validator should have run
        assert validator_calls == ["first"]
