import pytest


def test_validate():
    from pykour.schema import BaseSchema
    from pykour.validator import validate

    class UserSchema(BaseSchema):
        name: str

        @validate("name")
        def validate_name(self, value):
            if not value:
                raise ValueError("Name cannot be empty")

    user = UserSchema()
