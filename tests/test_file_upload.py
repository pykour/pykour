"""Tests for file upload functionality."""

import pytest

from pykour import File, Form, JSONResponse, Pykour, UploadFile
from pykour.datastructures import FormData
from pykour.testing import TestClient


class TestUploadFile:
    """Tests for UploadFile class."""

    async def test_read_content(self) -> None:
        """Test reading file content."""
        import io

        content = b"Hello, World!"
        file = io.BytesIO(content)
        upload = UploadFile(file=file, filename="test.txt")

        result = await upload.read()
        assert result == content
        assert upload.size == len(content)

    async def test_seek_and_read(self) -> None:
        """Test seeking and reading."""
        import io

        content = b"Hello, World!"
        file = io.BytesIO(content)
        upload = UploadFile(file=file, filename="test.txt")

        await upload.read()  # Read all
        await upload.seek(0)  # Seek to beginning
        result = await upload.read(5)  # Read first 5 bytes
        assert result == b"Hello"

    async def test_properties(self) -> None:
        """Test filename, content_type, and headers."""
        import io

        file = io.BytesIO(b"test")
        upload = UploadFile(
            file=file,
            filename="image.png",
            content_type="image/png",
            headers={"x-custom": "value"},
        )

        assert upload.filename == "image.png"
        assert upload.content_type == "image/png"
        assert upload.headers == {"x-custom": "value"}

    async def test_default_content_type(self) -> None:
        """Test default content type is application/octet-stream."""
        import io

        file = io.BytesIO(b"test")
        upload = UploadFile(file=file)

        assert upload.content_type == "application/octet-stream"

    async def test_write_and_read(self) -> None:
        """Test writing and reading."""
        import io

        file = io.BytesIO()
        upload = UploadFile(file=file, filename="new.txt")

        await upload.write(b"Hello")
        await upload.seek(0)
        result = await upload.read()
        assert result == b"Hello"

    def test_repr(self) -> None:
        """Test string representation."""
        import io

        file = io.BytesIO(b"test")
        upload = UploadFile(file=file, filename="test.txt", content_type="text/plain")

        assert "filename='test.txt'" in repr(upload)
        assert "content_type='text/plain'" in repr(upload)


class TestFormData:
    """Tests for FormData class."""

    def test_get_field(self) -> None:
        """Test getting form field."""
        form_data = FormData(fields={"name": "Alice"}, files={})
        assert form_data.get("name") == "Alice"
        assert form_data.fields["name"] == "Alice"

    def test_get_file(self) -> None:
        """Test getting uploaded file."""
        import io

        file = io.BytesIO(b"test")
        upload = UploadFile(file=file, filename="test.txt")
        form_data = FormData(fields={}, files={"avatar": upload})

        assert form_data.get("avatar") == upload
        assert form_data.files["avatar"] == upload

    def test_get_default(self) -> None:
        """Test getting with default value."""
        form_data = FormData(fields={}, files={})
        assert form_data.get("missing", "default") == "default"

    def test_repr(self) -> None:
        """Test string representation."""
        form_data = FormData(fields={"name": "Alice"}, files={"avatar": None})  # type: ignore
        rep = repr(form_data)
        assert "fields=" in rep
        assert "files=" in rep


class TestFileMarker:
    """Tests for File() marker."""

    def test_file_marker_defaults(self) -> None:
        """Test File() default values."""
        file_marker = File()
        assert not file_marker.has_default
        assert file_marker.max_size is None
        assert file_marker.allowed_types is None

    def test_file_marker_with_constraints(self) -> None:
        """Test File() with constraints."""
        file_marker = File(
            max_size=1024 * 1024,
            allowed_types=["image/jpeg", "image/png"],
            description="Profile picture",
        )
        assert file_marker.max_size == 1024 * 1024
        assert file_marker.allowed_types == ["image/jpeg", "image/png"]
        assert file_marker.description == "Profile picture"

    def test_file_marker_with_default(self) -> None:
        """Test File() with default value."""
        file_marker = File(default=None)
        assert file_marker.has_default
        assert file_marker.get_default() is None


class TestFormMarker:
    """Tests for Form() marker."""

    def test_form_marker_defaults(self) -> None:
        """Test Form() default values."""
        form_marker = Form()
        assert not form_marker.has_default

    def test_form_marker_with_default(self) -> None:
        """Test Form() with default value."""
        form_marker = Form(default="")
        assert form_marker.has_default
        assert form_marker.get_default() == ""

    def test_form_marker_with_alias(self) -> None:
        """Test Form() with alias."""
        form_marker = Form(alias="user_name")
        assert form_marker.alias == "user_name"


class TestFileUploadIntegration:
    """Integration tests for file upload."""

    @pytest.fixture
    def app(self) -> Pykour:
        """Create test app."""
        app = Pykour()

        async def upload_single(file: UploadFile = File()) -> JSONResponse:  # type: ignore[assignment]
            content = await file.read()
            return JSONResponse(
                {
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "size": len(content),
                }
            )

        async def upload_with_form(
            name: str = Form(),  # type: ignore[assignment]
            description: str = Form(default=""),  # type: ignore[assignment]
            file: UploadFile = File(),  # type: ignore[assignment]
        ) -> JSONResponse:
            content = await file.read()
            return JSONResponse(
                {
                    "name": name,
                    "description": description,
                    "filename": file.filename,
                    "size": len(content),
                }
            )

        async def upload_multiple(
            files: list[UploadFile] = File(),  # type: ignore[assignment]
        ) -> JSONResponse:
            results = []
            for f in files:
                content = await f.read()
                results.append({"filename": f.filename, "size": len(content)})
            return JSONResponse({"files": results})

        async def upload_optional(
            file: UploadFile | None = File(default=None),  # type: ignore[assignment]
        ) -> JSONResponse:
            if file is None:
                return JSONResponse({"has_file": False})
            content = await file.read()
            return JSONResponse({"has_file": True, "size": len(content)})

        app.register_route("/upload/single", {"POST": upload_single})
        app.register_route("/upload/with-form", {"POST": upload_with_form})
        app.register_route("/upload/multiple", {"POST": upload_multiple})
        app.register_route("/upload/optional", {"POST": upload_optional})

        return app

    @pytest.fixture
    def client(self, app: Pykour) -> TestClient:
        """Create test client."""
        return TestClient(app)

    async def test_upload_single_file(self, client: TestClient) -> None:
        """Test single file upload."""
        response = await client.post_multipart(
            "/upload/single",
            files={"file": ("test.txt", b"Hello, World!", "text/plain")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test.txt"
        # python-multipart doesn't expose content_type, defaults to octet-stream
        assert data["content_type"] == "application/octet-stream"
        assert data["size"] == 13

    async def test_upload_with_form_data(self, client: TestClient) -> None:
        """Test upload with form fields."""
        response = await client.post_multipart(
            "/upload/with-form",
            form_data={"name": "Alice", "description": "Test file"},
            files={"file": ("test.txt", b"Hello!", "text/plain")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Alice"
        assert data["description"] == "Test file"
        assert data["filename"] == "test.txt"
        assert data["size"] == 6

    async def test_upload_optional_without_file(self, client: TestClient) -> None:
        """Test optional file without providing file."""
        response = await client.post_multipart("/upload/optional", files={})

        assert response.status_code == 201
        data = response.json()
        assert data["has_file"] is False

    async def test_upload_optional_with_file(self, client: TestClient) -> None:
        """Test optional file with file."""
        response = await client.post_multipart(
            "/upload/optional",
            files={"file": ("test.txt", b"content", "text/plain")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["has_file"] is True
        assert data["size"] == 7

    async def test_missing_required_file(self, client: TestClient) -> None:
        """Test missing required file returns validation error."""
        response = await client.post_multipart("/upload/single", files={})

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    async def test_missing_required_form_field(self, client: TestClient) -> None:
        """Test missing required form field returns validation error."""
        response = await client.post_multipart(
            "/upload/with-form",
            form_data={},  # Missing required 'name' field
            files={"file": ("test.txt", b"content", "text/plain")},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestOpenAPIFileUpload:
    """Tests for OpenAPI schema generation with file uploads."""

    @pytest.fixture
    def app(self) -> Pykour:
        """Create test app."""
        app = Pykour()

        async def upload(
            name: str = Form(description="User name"),  # type: ignore[assignment]
            avatar: UploadFile = File(description="Profile picture"),  # type: ignore[assignment]
        ) -> JSONResponse:
            return JSONResponse({})

        app.register_route("/upload", {"POST": upload})

        return app

    def test_multipart_content_type(self, app: Pykour) -> None:
        """Test multipart/form-data content type in OpenAPI."""
        from pykour.openapi import OpenAPIConfig
        from pykour.openapi.generator import OpenAPIGenerator

        config = OpenAPIConfig(title="Test API", version="1.0.0")
        generator = OpenAPIGenerator(app._router, config)
        doc = generator.generate()

        # Get the upload endpoint
        upload_path = doc["paths"].get("/upload", {})
        post_op = upload_path.get("post", {})
        request_body = post_op.get("requestBody", {})
        content = request_body.get("content", {})

        assert "multipart/form-data" in content
        schema = content["multipart/form-data"]["schema"]
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "avatar" in schema["properties"]

    def test_file_schema_format(self, app: Pykour) -> None:
        """Test file field has binary format in OpenAPI."""
        from pykour.openapi import OpenAPIConfig
        from pykour.openapi.generator import OpenAPIGenerator

        config = OpenAPIConfig(title="Test API", version="1.0.0")
        generator = OpenAPIGenerator(app._router, config)
        doc = generator.generate()

        upload_path = doc["paths"].get("/upload", {})
        post_op = upload_path.get("post", {})
        schema = post_op["requestBody"]["content"]["multipart/form-data"]["schema"]

        avatar_schema = schema["properties"]["avatar"]
        assert avatar_schema["type"] == "string"
        assert avatar_schema["format"] == "binary"
