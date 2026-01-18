"""Integration tests for tus protocol middleware."""

import pytest

from pykour import Pykour
from pykour.testing import TestClient
from pykour.upload import TusMiddleware, MemoryUploadStorage


class TestTusMiddlewareIntegration:
    """Integration tests for TusMiddleware."""

    @pytest.fixture
    def storage(self) -> MemoryUploadStorage:
        """Create a memory storage."""
        return MemoryUploadStorage(max_size=10 * 1024 * 1024)  # 10MB

    @pytest.fixture
    def app(self, storage: MemoryUploadStorage) -> Pykour:
        """Create a Pykour app with TusMiddleware."""
        app = Pykour()
        app.add_middleware(
            TusMiddleware,
            storage=storage,
            path_prefix="/files",
            max_size=1024 * 1024,  # 1MB
        )
        return app

    @pytest.fixture
    def client(self, app: Pykour) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    async def test_options_request(self, client: TestClient) -> None:
        """Test OPTIONS request returns server capabilities."""
        response = await client.request(
            method="OPTIONS",
            path="/files",
            headers={},
        )

        assert response.status_code == 204
        assert response.headers.get("tus-resumable") == "1.0.0"
        assert "tus-version" in response.headers
        assert "tus-extension" in response.headers
        assert "tus-max-size" in response.headers

    async def test_create_upload(self, client: TestClient) -> None:
        """Test creating a new upload via POST."""
        response = await client.request(
            method="POST",
            path="/files",
            headers={
                "Tus-Resumable": "1.0.0",
                "Upload-Length": "100",
                "Upload-Metadata": "filename dGVzdC50eHQ=",
            },
        )

        assert response.status_code == 201
        assert "location" in response.headers
        assert response.headers.get("tus-resumable") == "1.0.0"
        assert response.headers.get("upload-offset") == "0"

    async def test_create_upload_missing_length(self, client: TestClient) -> None:
        """Test creating upload without Upload-Length returns error."""
        response = await client.request(
            method="POST",
            path="/files",
            headers={
                "Tus-Resumable": "1.0.0",
            },
        )

        assert response.status_code == 400

    async def test_create_upload_exceeds_max_size(self, client: TestClient) -> None:
        """Test creating upload exceeding max size returns error."""
        response = await client.request(
            method="POST",
            path="/files",
            headers={
                "Tus-Resumable": "1.0.0",
                "Upload-Length": "2000000000",  # 2GB > 1MB limit
            },
        )

        assert response.status_code == 413

    async def test_unsupported_version(self, client: TestClient) -> None:
        """Test unsupported tus version returns error."""
        response = await client.request(
            method="POST",
            path="/files",
            headers={
                "Tus-Resumable": "0.2.2",
                "Upload-Length": "100",
            },
        )

        assert response.status_code == 412

    async def test_full_upload_flow(
        self, client: TestClient, storage: MemoryUploadStorage
    ) -> None:
        """Test complete upload flow: create, upload chunks, verify."""
        # Create upload
        create_response = await client.request(
            method="POST",
            path="/files",
            headers={
                "Tus-Resumable": "1.0.0",
                "Upload-Length": "10",
                "Upload-Metadata": "filename dGVzdC50eHQ=",
            },
        )

        assert create_response.status_code == 201
        location = create_response.headers["location"]
        upload_path = "/" + "/".join(location.split("/")[-2:])

        # Check status (HEAD)
        head_response = await client.request(
            method="HEAD",
            path=upload_path,
            headers={
                "Tus-Resumable": "1.0.0",
            },
        )

        assert head_response.status_code == 200
        assert head_response.headers.get("upload-offset") == "0"
        assert head_response.headers.get("upload-length") == "10"

        # Upload first chunk (PATCH)
        patch_response = await client.request(
            method="PATCH",
            path=upload_path,
            headers={
                "Tus-Resumable": "1.0.0",
                "Upload-Offset": "0",
                "Content-Type": "application/offset+octet-stream",
            },
            data=b"Hello",
        )

        assert patch_response.status_code == 204
        assert patch_response.headers.get("upload-offset") == "5"

        # Check status after first chunk
        head_response = await client.request(
            method="HEAD",
            path=upload_path,
            headers={
                "Tus-Resumable": "1.0.0",
            },
        )

        assert head_response.headers.get("upload-offset") == "5"

        # Upload second chunk to complete
        patch_response = await client.request(
            method="PATCH",
            path=upload_path,
            headers={
                "Tus-Resumable": "1.0.0",
                "Upload-Offset": "5",
                "Content-Type": "application/offset+octet-stream",
            },
            data=b"World",
        )

        assert patch_response.status_code == 204
        assert patch_response.headers.get("upload-offset") == "10"

        # Verify data in storage
        upload_id = upload_path.split("/")[-1]
        data = storage.get_data(upload_id)
        assert data == b"HelloWorld"

    async def test_patch_wrong_offset(
        self, client: TestClient, storage: MemoryUploadStorage
    ) -> None:
        """Test PATCH with wrong offset returns conflict error."""
        # Create upload
        create_response = await client.request(
            method="POST",
            path="/files",
            headers={
                "Tus-Resumable": "1.0.0",
                "Upload-Length": "100",
            },
        )
        location = create_response.headers["location"]
        upload_path = "/" + "/".join(location.split("/")[-2:])

        # Try PATCH with wrong offset
        response = await client.request(
            method="PATCH",
            path=upload_path,
            headers={
                "Tus-Resumable": "1.0.0",
                "Upload-Offset": "50",  # Wrong - should be 0
                "Content-Type": "application/offset+octet-stream",
            },
            data=b"Hello",
        )

        assert response.status_code == 409

    async def test_patch_wrong_content_type(
        self, client: TestClient, storage: MemoryUploadStorage
    ) -> None:
        """Test PATCH with wrong Content-Type returns error."""
        # Create upload
        create_response = await client.request(
            method="POST",
            path="/files",
            headers={
                "Tus-Resumable": "1.0.0",
                "Upload-Length": "100",
            },
        )
        location = create_response.headers["location"]
        upload_path = "/" + "/".join(location.split("/")[-2:])

        # Try PATCH with wrong content type
        response = await client.request(
            method="PATCH",
            path=upload_path,
            headers={
                "Tus-Resumable": "1.0.0",
                "Upload-Offset": "0",
                "Content-Type": "application/json",  # Wrong type
            },
            data=b"Hello",
        )

        assert response.status_code == 400

    async def test_delete_upload(
        self, client: TestClient, storage: MemoryUploadStorage
    ) -> None:
        """Test DELETE cancels an upload."""
        # Create upload
        create_response = await client.request(
            method="POST",
            path="/files",
            headers={
                "Tus-Resumable": "1.0.0",
                "Upload-Length": "100",
            },
        )
        location = create_response.headers["location"]
        upload_path = "/" + "/".join(location.split("/")[-2:])

        # Delete upload
        delete_response = await client.request(
            method="DELETE",
            path=upload_path,
            headers={
                "Tus-Resumable": "1.0.0",
            },
        )

        assert delete_response.status_code == 204

        # Verify it's gone (HEAD should 404)
        head_response = await client.request(
            method="HEAD",
            path=upload_path,
            headers={
                "Tus-Resumable": "1.0.0",
            },
        )

        assert head_response.status_code == 404

    async def test_head_not_found(self, client: TestClient) -> None:
        """Test HEAD for non-existent upload returns 404."""
        response = await client.request(
            method="HEAD",
            path="/files/non-existent-id",
            headers={
                "Tus-Resumable": "1.0.0",
            },
        )

        assert response.status_code == 404

    async def test_cors_headers(self, client: TestClient) -> None:
        """Test CORS headers are included in responses."""
        response = await client.request(
            method="OPTIONS",
            path="/files",
            headers={
                "Origin": "https://example.com",
            },
        )

        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    async def test_non_tus_request_passes_through(self, client: TestClient) -> None:
        """Test requests without Tus-Resumable header pass through."""
        # Request to /files without Tus-Resumable should pass to app
        # Since no route is defined, should get 404 from app (not from tus)
        response = await client.get("/files")

        # This should be a standard 404, not a tus response
        assert response.status_code == 404

    async def test_request_to_other_path_passes_through(
        self, client: TestClient
    ) -> None:
        """Test requests to non-tus paths pass through."""
        response = await client.request(
            method="POST",
            path="/other",
            headers={
                "Tus-Resumable": "1.0.0",
            },
        )

        # Should pass through to app and get 404 (no route defined)
        assert response.status_code == 404
