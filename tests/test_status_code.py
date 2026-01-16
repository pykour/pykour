"""Tests for status_code decorator."""

from typing import Any


from pykour.status_code import (
    STATUS_CODE_REGISTRY_ATTR,
    StatusCodeInfo,
    get_default_status_code,
    get_method_default_status_code,
    get_status_code_info,
    status_code,
)


class TestStatusCodeDecorator:
    """Tests for @status_code decorator."""

    def test_status_code_adds_metadata(self) -> None:
        """Test that @status_code adds StatusCodeInfo metadata to function."""

        @status_code(201, description="Created")
        async def create_user() -> dict[str, Any]:
            return {"id": 1}

        assert hasattr(create_user, STATUS_CODE_REGISTRY_ATTR)
        infos = getattr(create_user, STATUS_CODE_REGISTRY_ATTR)
        assert len(infos) == 1
        assert infos[0].code == 201
        assert infos[0].description == "Created"
        assert infos[0].is_default is True

    def test_status_code_without_description(self) -> None:
        """Test @status_code without description."""

        @status_code(204)
        async def delete_user() -> None:
            pass

        infos = get_status_code_info(delete_user)
        assert len(infos) == 1
        assert infos[0].code == 204
        assert infos[0].description is None

    def test_status_code_stacking(self) -> None:
        """Test multiple @status_code decorators on same function."""

        @status_code(200, description="Success")
        @status_code(404, description="Not Found", is_default=False)
        async def get_user() -> dict[str, Any]:
            return {}

        infos = get_status_code_info(get_user)
        assert len(infos) == 2
        # Order: innermost first
        assert infos[0].code == 404
        assert infos[1].code == 200

    def test_get_default_status_code(self) -> None:
        """Test get_default_status_code returns first default."""

        @status_code(201, description="Created")
        @status_code(409, description="Conflict", is_default=False)
        async def create_item() -> dict[str, Any]:
            return {}

        default = get_default_status_code(create_item)
        assert default == 201

    def test_get_default_status_code_with_non_default_first(self) -> None:
        """Test get_default_status_code finds default when non-default is first."""

        @status_code(404, description="Not Found", is_default=False)
        @status_code(200, description="Success", is_default=True)
        async def handler() -> dict[str, Any]:
            return {}

        default = get_default_status_code(handler)
        assert default == 200

    def test_get_default_status_code_none(self) -> None:
        """Test get_default_status_code returns None when no default."""

        @status_code(404, description="Not Found", is_default=False)
        async def handler() -> dict[str, Any]:
            return {}

        default = get_default_status_code(handler)
        assert default is None

    def test_no_decorator(self) -> None:
        """Test functions without decorator."""

        async def plain_func() -> dict[str, Any]:
            return {}

        infos = get_status_code_info(plain_func)
        assert infos == []

        default = get_default_status_code(plain_func)
        assert default is None

    def test_sync_function(self) -> None:
        """Test decorator works with sync functions."""

        @status_code(201)
        def sync_handler() -> dict[str, Any]:
            return {"id": 1}

        infos = get_status_code_info(sync_handler)
        assert len(infos) == 1
        assert infos[0].code == 201


class TestStatusCodeInfo:
    """Tests for StatusCodeInfo dataclass."""

    def test_defaults(self) -> None:
        """Test StatusCodeInfo default values."""
        info = StatusCodeInfo(code=200)
        assert info.code == 200
        assert info.description is None
        assert info.is_default is True

    def test_with_all_values(self) -> None:
        """Test StatusCodeInfo with all values."""
        info = StatusCodeInfo(code=201, description="Created", is_default=True)
        assert info.code == 201
        assert info.description == "Created"
        assert info.is_default is True

    def test_non_default(self) -> None:
        """Test StatusCodeInfo with is_default=False."""
        info = StatusCodeInfo(code=404, description="Not Found", is_default=False)
        assert info.code == 404
        assert info.description == "Not Found"
        assert info.is_default is False


class TestMethodDefaultStatusCode:
    """Tests for get_method_default_status_code function."""

    def test_post_returns_201(self) -> None:
        """Test POST method returns 201 Created."""
        assert get_method_default_status_code("POST") == 201
        assert get_method_default_status_code("post") == 201

    def test_delete_returns_204(self) -> None:
        """Test DELETE method returns 204 No Content."""
        assert get_method_default_status_code("DELETE") == 204
        assert get_method_default_status_code("delete") == 204

    def test_get_returns_200(self) -> None:
        """Test GET method returns 200 OK."""
        assert get_method_default_status_code("GET") == 200
        assert get_method_default_status_code("get") == 200

    def test_put_returns_200(self) -> None:
        """Test PUT method returns 200 OK."""
        assert get_method_default_status_code("PUT") == 200
        assert get_method_default_status_code("put") == 200

    def test_patch_returns_200(self) -> None:
        """Test PATCH method returns 200 OK."""
        assert get_method_default_status_code("PATCH") == 200
        assert get_method_default_status_code("patch") == 200

    def test_unknown_method_returns_200(self) -> None:
        """Test unknown method returns 200 OK as default."""
        assert get_method_default_status_code("UNKNOWN") == 200
        assert get_method_default_status_code("OPTIONS") == 200
