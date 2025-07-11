import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from io import BytesIO
from PIL import Image

from ehp.core.models.db.authentication import Authentication
from ehp.core.models.db.user import User
from ehp.tests.utils.test_client import EHPTestClient
from ehp.utils.authentication import hash_password
from ehp.config import settings


@pytest.mark.integration
class TestAvatarUploadEndpoint:
    """Integration tests for the /users/me/avatar endpoint."""

    @pytest.fixture
    def valid_user_data(self):
        """Valid user data for testing."""
        return {
            "user_id": 123,
            "auth_id": 456,
            "full_name": "Test User",
            "email": "test@example.com"
        }

    @pytest.fixture
    def mock_user(self, valid_user_data):
        """Mock user record without avatar."""
        return User(
            id=valid_user_data["user_id"],
            auth_id=valid_user_data["auth_id"],
            full_name=valid_user_data["full_name"],
            avatar=None
        )

    @pytest.fixture
    def mock_authentication(self, valid_user_data, mock_user):
        """Mock authentication record."""
        auth = Authentication(
            id=valid_user_data["auth_id"],
            user_email=valid_user_data["email"],
            user_name=valid_user_data["email"],
            user_pwd=hash_password("password123"),
            is_active="1",
            is_confirmed="1"
        )
        auth.user = mock_user
        return auth

    @pytest.fixture
    def create_test_image(self):
        """Create a test PNG image file."""
        
        def _create_image(format='PNG', size=(100, 100), file_size_kb=None):
            """Create test image with specified format and approximate size."""
            img = Image.new('RGB', size, color='red')
            img_bytes = BytesIO()
            img.save(img_bytes, format=format)
            
            if file_size_kb:
                # Adjust quality to get approximate file size
                img_bytes = BytesIO()
                if format.upper() == 'JPEG':
                    quality = max(10, min(95, 100 - (file_size_kb // 10)))
                    img.save(img_bytes, format=format, quality=quality)
                else:
                    img.save(img_bytes, format=format)
            
            img_bytes.seek(0)
            return img_bytes.getvalue()
        
        return _create_image

    @pytest.fixture
    def avatar_upload_mocks(self, test_client: EHPTestClient, mock_authentication, mock_user, aws_mock):
        """Fixture to setup common mocks for avatar upload tests."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        
        # Setup dependency overrides
        test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
        test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
        
        # Setup context managers for mocking (only what we need to mock)
        repo_patch = patch('ehp.core.services.user.UserRepository')
        session_patch = patch('ehp.db.db_manager.ManagedAsyncSession')
        aws_client_patch = patch('ehp.core.services.user.AWSClient')
        
        # Start patches
        mock_user_repo = repo_patch.start()
        mock_session = session_patch.start()
        mock_aws_client = aws_client_patch.start()
        
        # Use the real moto S3 client from aws_mock
        mock_aws_client.return_value = aws_mock
        
        mock_repo_instance = AsyncMock()
        mock_user_repo.return_value = mock_repo_instance
        
        # Setup mock user with updated avatar (default)
        updated_user = User(
            id=mock_user.id,
            auth_id=mock_user.auth_id,
            full_name=mock_user.full_name,
            avatar=f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION_NAME}.amazonaws.com/avatars/test.png"
        )
        mock_repo_instance.update_avatar.return_value = updated_user
        
        # Yield the mock instances for test customization
        yield {
            'aws_client': aws_mock,
            'user_repo': mock_user_repo,
            'repo_instance': mock_repo_instance,
            'session': mock_session,
            'updated_user': updated_user
        }
        
        # Cleanup
        repo_patch.stop()
        session_patch.stop()
        aws_client_patch.stop()
        test_client.app.dependency_overrides.clear()

    def test_upload_avatar_success(
        self, test_client: EHPTestClient, avatar_upload_mocks, create_test_image
    ):
        """Test successful avatar upload."""
        # Create test image
        image_data = create_test_image('PNG', (100, 100))
        
        response = test_client.post(
            "/users/me/avatar",
            files={"avatar": ("test.png", image_data, "image/png")},
            include_auth=True
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert "avatar_url" in response_data
        assert "message" in response_data
        assert response_data["message"] == "Avatar uploaded successfully"
        assert "avatars/" in response_data["avatar_url"]
        
        # Verify that the file was uploaded to S3 (check bucket contents)
        s3_client = avatar_upload_mocks['aws_client'].s3_client
        objects = s3_client.list_objects_v2(Bucket=settings.AWS_S3_BUCKET)
        assert 'Contents' in objects
        assert len(objects['Contents']) > 0
        assert any('avatars/' in obj['Key'] for obj in objects['Contents'])
        
        # Verify user repository update was called
        avatar_upload_mocks['repo_instance'].update_avatar.assert_called_once()

    def test_upload_avatar_file_too_large(
        self, test_client: EHPTestClient, mock_authentication, create_test_image
    ):
        """Test avatar upload with file exceeding size limit."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        
        # Create large image (> 500KB)
        large_image_data = b'x' * (600 * 1024)  # 600KB
        
        # Override FastAPI dependencies
        test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
        test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
        
        try:
            response = test_client.post(
                "/users/me/avatar",
                files={"avatar": ("large.png", large_image_data, "image/png")},
                include_auth=True
            )
            
            assert response.status_code == 413
            response_data = response.json()
            assert "detail" in response_data
            assert "File size exceeds 500KB limit" in response_data["detail"]
            
        finally:
            test_client.app.dependency_overrides.clear()

    def test_upload_avatar_invalid_format(
        self, test_client: EHPTestClient, mock_authentication
    ):
        """Test avatar upload with invalid file format."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        
        # Create text file instead of image
        text_data = b"This is not an image file"
        
        # Override FastAPI dependencies
        test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
        test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
        
        try:
            response = test_client.post(
                "/users/me/avatar",
                files={"avatar": ("document.txt", text_data, "text/plain")},
                include_auth=True
            )
            
            assert response.status_code == 400
            response_data = response.json()
            assert "detail" in response_data
            assert "Only PNG, JPG, JPEG, and WebP formats are allowed" in response_data["detail"]
            
        finally:
            test_client.app.dependency_overrides.clear()

    def test_upload_avatar_invalid_image_content(
        self, test_client: EHPTestClient, mock_authentication
    ):
        """Test avatar upload with invalid image content."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        
        # Create fake PNG file (wrong content)
        fake_image_data = b"fake png content"
        
        # Override FastAPI dependencies
        test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
        test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
        
        try:
            response = test_client.post(
                "/users/me/avatar",
                files={"avatar": ("fake.png", fake_image_data, "image/png")},
                include_auth=True
            )
            
            assert response.status_code == 400
            response_data = response.json()
            assert "detail" in response_data
            assert "Invalid image file" in response_data["detail"]
            
        finally:
            test_client.app.dependency_overrides.clear()

    def test_upload_avatar_unauthenticated(self, test_client: EHPTestClient, create_test_image):
        """Test avatar upload without authentication."""
        image_data = create_test_image('PNG', (100, 100))
        
        response = test_client.post(
            "/users/me/avatar",
            files={"avatar": ("test.png", image_data, "image/png")},
            include_auth=False
        )
        
        # Should return 401 or 403 depending on authentication setup
        assert response.status_code in [401, 403]

    def test_upload_avatar_s3_error(
        self, test_client: EHPTestClient, avatar_upload_mocks, create_test_image
    ):
        """Test avatar upload when S3 upload fails."""
        image_data = create_test_image('PNG', (100, 100))
        
        # Mock the S3 client put_object method to raise an exception
        from unittest.mock import patch
        with patch.object(avatar_upload_mocks['aws_client'].s3_client, 'put_object', side_effect=Exception("S3 error")):
            response = test_client.post(
                "/users/me/avatar",
                files={"avatar": ("test.png", image_data, "image/png")},
                include_auth=True
            )
        
        assert response.status_code == 500
        response_data = response.json()
        assert "detail" in response_data
        assert "Failed to upload avatar" in response_data["detail"]

    def test_upload_avatar_webp_format(
        self, test_client: EHPTestClient, avatar_upload_mocks, create_test_image
    ):
        """Test successful avatar upload with WebP format."""
        # Create WebP test image
        image_data = create_test_image('WEBP', (100, 100))
        
        # Update the expected avatar URL for WebP format
        avatar_upload_mocks['updated_user'].avatar = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION_NAME}.amazonaws.com/avatars/test.webp"
        
        response = test_client.post(
            "/users/me/avatar",
            files={"avatar": ("test.webp", image_data, "image/webp")},
            include_auth=True
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert "avatar_url" in response_data
        assert "message" in response_data
        assert response_data["message"] == "Avatar uploaded successfully"
        
        # Verify that the file was uploaded to S3 (check bucket contents)
        s3_client = avatar_upload_mocks['aws_client'].s3_client
        objects = s3_client.list_objects_v2(Bucket=settings.AWS_S3_BUCKET)
        assert 'Contents' in objects
        assert len(objects['Contents']) > 0
        assert any('avatars/' in obj['Key'] for obj in objects['Contents'])
        
        # Verify user repository update was called
        avatar_upload_mocks['repo_instance'].update_avatar.assert_called_once()
