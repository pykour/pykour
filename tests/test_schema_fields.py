"""Tests for schema field definitions and validators."""

from __future__ import annotations

import pytest

from pykour.schema.fields import (
    MISSING,
    Body,
    Field,
    FieldInfo,
    Path,
    Query,
)
from pykour.schema.validators import (
    Constraint,
    Ge,
    Gt,
    Le,
    Lt,
    MaxLength,
    MinLength,
    Pattern,
)


class TestMISSING:
    """Tests for MISSING sentinel."""

    def test_missing_is_unique(self) -> None:
        """MISSING is a unique sentinel object."""
        assert MISSING is MISSING
        assert MISSING is not None
        assert MISSING != None  # noqa: E711

    def test_missing_is_falsy_check(self) -> None:
        """MISSING should be checked with 'is' not '=='."""
        some_value = object()
        assert some_value is not MISSING
        assert MISSING is MISSING


class TestFieldInfo:
    """Tests for FieldInfo class."""

    def test_default_values(self) -> None:
        """FieldInfo has correct default values."""
        field = FieldInfo()
        assert field.default is MISSING
        assert field.default_factory is None
        assert field.alias is None
        assert field.ge is None
        assert field.le is None
        assert field.gt is None
        assert field.lt is None
        assert field.min_length is None
        assert field.max_length is None
        assert field.pattern is None
        assert field.description is None

    def test_with_default_value(self) -> None:
        """FieldInfo can have a default value."""
        field = FieldInfo(default=42)
        assert field.default == 42
        assert field.has_default is True
        assert field.get_default() == 42

    def test_with_default_factory(self) -> None:
        """FieldInfo can have a default factory."""
        field = FieldInfo(default_factory=list)
        assert field.default is MISSING
        assert field.default_factory is list
        assert field.has_default is True
        default = field.get_default()
        assert isinstance(default, list)

    def test_default_factory_creates_new_instances(self) -> None:
        """Default factory creates new instance each time."""
        field = FieldInfo(default_factory=list)
        default1 = field.get_default()
        default2 = field.get_default()
        assert default1 is not default2

    def test_cannot_have_both_default_and_factory(self) -> None:
        """Cannot specify both default and default_factory."""
        with pytest.raises(ValueError, match="Cannot specify both"):
            FieldInfo(default=42, default_factory=list)

    def test_has_default_without_defaults(self) -> None:
        """has_default returns False when no default is set."""
        field = FieldInfo()
        assert field.has_default is False

    def test_get_default_returns_missing(self) -> None:
        """get_default returns MISSING when no default is set."""
        field = FieldInfo()
        assert field.get_default() is MISSING

    def test_with_alias(self) -> None:
        """FieldInfo can have an alias."""
        field = FieldInfo(alias="my_alias")
        assert field.alias == "my_alias"

    def test_with_description(self) -> None:
        """FieldInfo can have a description."""
        field = FieldInfo(description="A test field")
        assert field.description == "A test field"

    def test_with_numeric_constraints(self) -> None:
        """FieldInfo can have numeric constraints."""
        field = FieldInfo(ge=0, le=100, gt=-1, lt=101)
        assert field.ge == 0
        assert field.le == 100
        assert field.gt == -1
        assert field.lt == 101

    def test_with_string_constraints(self) -> None:
        """FieldInfo can have string constraints."""
        field = FieldInfo(min_length=1, max_length=10, pattern=r"^\w+$")
        assert field.min_length == 1
        assert field.max_length == 10
        assert field.pattern == r"^\w+$"

    def test_get_constraints_empty(self) -> None:
        """get_constraints returns empty list when no constraints set."""
        field = FieldInfo()
        constraints = field.get_constraints()
        assert constraints == []

    def test_get_constraints_numeric(self) -> None:
        """get_constraints returns numeric constraints."""
        field = FieldInfo(ge=0, le=100, gt=-1, lt=101)
        constraints = field.get_constraints()
        assert len(constraints) == 4
        assert any(isinstance(c, Ge) for c in constraints)
        assert any(isinstance(c, Le) for c in constraints)
        assert any(isinstance(c, Gt) for c in constraints)
        assert any(isinstance(c, Lt) for c in constraints)

    def test_get_constraints_string(self) -> None:
        """get_constraints returns string constraints."""
        field = FieldInfo(min_length=1, max_length=10, pattern=r"^\w+$")
        constraints = field.get_constraints()
        assert len(constraints) == 3
        assert any(isinstance(c, MinLength) for c in constraints)
        assert any(isinstance(c, MaxLength) for c in constraints)
        assert any(isinstance(c, Pattern) for c in constraints)


class TestFieldFunction:
    """Tests for Field() factory function."""

    def test_field_returns_fieldinfo(self) -> None:
        """Field() returns a FieldInfo instance."""
        field = Field()
        assert isinstance(field, FieldInfo)

    def test_field_with_default(self) -> None:
        """Field() can set default value."""
        field = Field(default=42)
        assert field.default == 42

    def test_field_with_all_params(self) -> None:
        """Field() passes all parameters to FieldInfo."""
        field = Field(
            default=0,
            alias="num",
            ge=0,
            le=100,
            description="A number",
        )
        assert field.default == 0
        assert field.alias == "num"
        assert field.ge == 0
        assert field.le == 100
        assert field.description == "A number"


class TestPathField:
    """Tests for Path marker class."""

    def test_path_is_fieldinfo(self) -> None:
        """Path is a subclass of FieldInfo."""
        path = Path()
        assert isinstance(path, FieldInfo)

    def test_path_with_constraints(self) -> None:
        """Path can have validation constraints."""
        path = Path(ge=1)
        assert path.ge == 1
        constraints = path.get_constraints()
        assert len(constraints) == 1
        assert isinstance(constraints[0], Ge)


class TestQueryField:
    """Tests for Query marker class."""

    def test_query_is_fieldinfo(self) -> None:
        """Query is a subclass of FieldInfo."""
        query = Query()
        assert isinstance(query, FieldInfo)

    def test_query_with_default(self) -> None:
        """Query can have a default value."""
        query = Query(default=1)
        assert query.default == 1
        assert query.has_default is True

    def test_query_with_alias(self) -> None:
        """Query can have an alias for different param name."""
        query = Query(alias="page_num")
        assert query.alias == "page_num"

    def test_query_with_constraints(self) -> None:
        """Query can have validation constraints."""
        query = Query(default=1, ge=1, le=100)
        assert query.ge == 1
        assert query.le == 100


class TestBodyField:
    """Tests for Body marker class."""

    def test_body_is_fieldinfo(self) -> None:
        """Body is a subclass of FieldInfo."""
        body = Body()
        assert isinstance(body, FieldInfo)


class TestConstraintBase:
    """Tests for Constraint base class."""

    def test_constraint_validate_not_implemented(self) -> None:
        """Constraint.validate raises NotImplementedError."""
        constraint = Constraint()
        with pytest.raises(NotImplementedError):
            constraint.validate("value", "field")


class TestGeConstraint:
    """Tests for Ge (greater than or equal) constraint."""

    def test_ge_valid(self) -> None:
        """Ge constraint passes for values >= limit."""
        ge = Ge(10)
        ge.validate(10, "field")  # Equal
        ge.validate(11, "field")  # Greater

    def test_ge_invalid(self) -> None:
        """Ge constraint fails for values < limit."""
        ge = Ge(10)
        with pytest.raises(ValueError, match="must be >= 10"):
            ge.validate(9, "field")

    def test_ge_with_float(self) -> None:
        """Ge constraint works with floats."""
        ge = Ge(10.5)
        ge.validate(10.5, "field")
        ge.validate(11.0, "field")
        with pytest.raises(ValueError):
            ge.validate(10.4, "field")


class TestGtConstraint:
    """Tests for Gt (greater than) constraint."""

    def test_gt_valid(self) -> None:
        """Gt constraint passes for values > limit."""
        gt = Gt(10)
        gt.validate(11, "field")

    def test_gt_invalid_equal(self) -> None:
        """Gt constraint fails for values == limit."""
        gt = Gt(10)
        with pytest.raises(ValueError, match="must be > 10"):
            gt.validate(10, "field")

    def test_gt_invalid_less(self) -> None:
        """Gt constraint fails for values < limit."""
        gt = Gt(10)
        with pytest.raises(ValueError, match="must be > 10"):
            gt.validate(9, "field")


class TestLeConstraint:
    """Tests for Le (less than or equal) constraint."""

    def test_le_valid(self) -> None:
        """Le constraint passes for values <= limit."""
        le = Le(10)
        le.validate(10, "field")  # Equal
        le.validate(9, "field")  # Less

    def test_le_invalid(self) -> None:
        """Le constraint fails for values > limit."""
        le = Le(10)
        with pytest.raises(ValueError, match="must be <= 10"):
            le.validate(11, "field")


class TestLtConstraint:
    """Tests for Lt (less than) constraint."""

    def test_lt_valid(self) -> None:
        """Lt constraint passes for values < limit."""
        lt = Lt(10)
        lt.validate(9, "field")

    def test_lt_invalid_equal(self) -> None:
        """Lt constraint fails for values == limit."""
        lt = Lt(10)
        with pytest.raises(ValueError, match="must be < 10"):
            lt.validate(10, "field")

    def test_lt_invalid_greater(self) -> None:
        """Lt constraint fails for values > limit."""
        lt = Lt(10)
        with pytest.raises(ValueError, match="must be < 10"):
            lt.validate(11, "field")


class TestMinLengthConstraint:
    """Tests for MinLength constraint."""

    def test_minlength_valid(self) -> None:
        """MinLength constraint passes for long enough values."""
        min_len = MinLength(3)
        min_len.validate("abc", "field")  # Equal
        min_len.validate("abcd", "field")  # Longer
        min_len.validate([1, 2, 3], "field")  # List

    def test_minlength_invalid(self) -> None:
        """MinLength constraint fails for too short values."""
        min_len = MinLength(3)
        with pytest.raises(ValueError, match="length must be >= 3"):
            min_len.validate("ab", "field")


class TestMaxLengthConstraint:
    """Tests for MaxLength constraint."""

    def test_maxlength_valid(self) -> None:
        """MaxLength constraint passes for short enough values."""
        max_len = MaxLength(3)
        max_len.validate("abc", "field")  # Equal
        max_len.validate("ab", "field")  # Shorter
        max_len.validate([1, 2], "field")  # List

    def test_maxlength_invalid(self) -> None:
        """MaxLength constraint fails for too long values."""
        max_len = MaxLength(3)
        with pytest.raises(ValueError, match="length must be <= 3"):
            max_len.validate("abcd", "field")


class TestPatternConstraint:
    """Tests for Pattern constraint."""

    def test_pattern_valid(self) -> None:
        """Pattern constraint passes for matching values."""
        pattern = Pattern(r"^\d{3}-\d{4}$")
        pattern.validate("123-4567", "field")

    def test_pattern_invalid(self) -> None:
        """Pattern constraint fails for non-matching values."""
        pattern = Pattern(r"^\d{3}-\d{4}$")
        with pytest.raises(ValueError, match="does not match pattern"):
            pattern.validate("12-3456", "field")

    def test_pattern_with_word_pattern(self) -> None:
        """Pattern constraint works with word patterns."""
        pattern = Pattern(r"^\w+$")
        pattern.validate("hello123", "field")
        with pytest.raises(ValueError):
            pattern.validate("hello world", "field")

    def test_pattern_email_like(self) -> None:
        """Pattern constraint works with email-like patterns."""
        pattern = Pattern(r"^[\w.]+@[\w.]+\.\w+$")
        pattern.validate("test@example.com", "field")
        with pytest.raises(ValueError):
            pattern.validate("invalid-email", "field")


class TestFieldImports:
    """Tests for field module imports."""

    def test_import_from_schema_module(self) -> None:
        """Fields can be imported from pykour.schema."""
        from pykour.schema import Body, Field, Path, Query

        assert Field is not None
        assert Path is not None
        assert Query is not None
        assert Body is not None

    def test_import_fieldinfo_from_fields(self) -> None:
        """FieldInfo can be imported from fields module."""
        from pykour.schema.fields import FieldInfo

        assert FieldInfo is not None
