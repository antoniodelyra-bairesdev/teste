import pytest
from unittest.mock import patch, AsyncMock
from fastapi import FastAPI

from ehp.core.models.db.authentication import Authentication
from ehp.core.models.db.user import User
from ehp.tests.utils.test_client import EHPTestClient
from ehp.utils.authentication import hash_password


@pytest.mark.integration
class TestPasswordChangeEndpoint:
    """Integration tests for the /users/me/password endpoint."""

    @pytest.fixture
    def valid_user_data(self):
        """Valid user data for testing."""
        return {
            "user_id": 123,
            "auth_id": 456,
            "full_name": "Test User",
            "email": "test@example.com",
            "current_password": "CurrentPass123",
            "new_password": "NewSecurePa$s123"
        }

    @pytest.fixture
    def mock_user(self, valid_user_data):
        """Mock user record."""
        return User(
            id=valid_user_data["user_id"],
            auth_id=valid_user_data["auth_id"],
            full_name=valid_user_data["full_name"]
        )

    @pytest.fixture
    def mock_authentication(self, valid_user_data, mock_user):
        """Mock authentication record."""
        auth = Authentication(
            id=valid_user_data["auth_id"],
            user_email=valid_user_data["email"],
            user_name=valid_user_data["email"],
            user_pwd=hash_password(valid_user_data["current_password"]),
            is_active="1",
            is_confirmed="1"
        )
        # Set up the user relationship
        auth.user = mock_user
        return auth

    @pytest.fixture
    def valid_password_change_data(self, valid_user_data):
        """Valid password change data."""
        return {
            "current_password": valid_user_data["current_password"],
            "new_password": valid_user_data["new_password"],
            "confirm_password": valid_user_data["new_password"]
        }

    def test_password_change_wrong_current_password(
        self, test_client: EHPTestClient, mock_authentication, mock_user
    ):
        """Test password change with wrong current password."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        
        # Override FastAPI dependencies
        test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
        test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
        
        try:
            with patch('ehp.core.services.user.AuthenticationRepository') as mock_auth_repo:
                mock_repo_instance = AsyncMock()
                mock_auth_repo.return_value = mock_repo_instance
                mock_repo_instance.get_by_id.return_value = mock_authentication
                
                password_data = {
                    "current_password": "WrongPassword123",
                    "new_password": "NewSecurePa$s123",
                    "confirm_password": "NewSecurePa$s123"
                }
                
                response = test_client.put(
                    "/users/me/password",
                    json=password_data,
                    include_auth=True
                )
                
                assert response.status_code == 400
                response_data = response.json()
                assert "detail" in response_data
                assert "Current password is incorrect" in response_data["detail"]
        finally:
            # Clean up dependency overrides
            test_client.app.dependency_overrides.clear()

    def test_password_change_invalid_new_password_too_short(
        self, test_client: EHPTestClient, mock_authentication, mock_user
    ):
        """Test password change with new password that's too short."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        
        # Override FastAPI dependencies
        test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
        test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
        
        try:
            password_data = {
                "current_password": "CurrentPass123",
                "new_password": "short",
                "confirm_password": "short"
            }
            
            response = test_client.put(
                "/users/me/password",
                json=password_data,
                include_auth=True
            )
            
            assert response.status_code == 422
            response_data = response.json()
            assert "detail" in response_data
            assert any(
                "Password must be at least 8 characters" in d["msg"]
                for d in response_data["detail"]
            )
        finally:
            test_client.app.dependency_overrides.clear()

    def test_password_change_invalid_new_password_no_uppercase(
        self, test_client: EHPTestClient, mock_authentication, mock_user
    ):
        """Test password change with new password missing uppercase letter."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        
        # Override FastAPI dependencies
        test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
        test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
        
        try:
            password_data = {
                "current_password": "CurrentPass123",
                "new_password": "lowercase123",
                "confirm_password": "lowercase123"
            }
            
            response = test_client.put(
                "/users/me/password",
                json=password_data,
                include_auth=True
            )
            
            assert response.status_code == 422
            response_data = response.json()
            assert "detail" in response_data
            assert any(
                "uppercase" in d["msg"].lower() for d in response_data["detail"]
            )
        finally:
            test_client.app.dependency_overrides.clear()

    def test_password_change_invalid_new_password_no_lowercase(
        self, test_client: EHPTestClient, mock_authentication, mock_user
    ):
        """Test password change with new password missing lowercase letter."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        
        # Override FastAPI dependencies
        test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
        test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
        
        try:
            password_data = {
                "current_password": "CurrentPass123",
                "new_password": "UPPERCASE123",
                "confirm_password": "UPPERCASE123"
            }
            
            response = test_client.put(
                "/users/me/password",
                json=password_data,
                include_auth=True
            )
            
            assert response.status_code == 422
            response_data = response.json()
            assert "detail" in response_data
            assert any(
                "lowercase" in d["msg"].lower() for d in response_data["detail"]
            )
        finally:
            test_client.app.dependency_overrides.clear()

    def test_password_change_passwords_dont_match(
        self, test_client: EHPTestClient, mock_authentication, mock_user
    ):
        """Test password change when new password and confirm password don't match."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        
        # Override FastAPI dependencies
        test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
        test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
        
        try:
            password_data = {
                "current_password": "CurrentPass123",
                "new_password": "NewSecurePa$s123",
                "confirm_password": "DifferentPa$sword123"
            }
            
            response = test_client.put(
                "/users/me/password",
                json=password_data,
                include_auth=True
            )
            
            assert response.status_code == 422
            response_data = response.json()
            assert "detail" in response_data
            assert any(
                "Passwords do not match" in d["msg"]
                for d in response_data["detail"]
            )
        finally:
            test_client.app.dependency_overrides.clear()

    def test_password_change_success(
        self, test_client: EHPTestClient, mock_authentication, mock_user, valid_password_change_data
    ):
        """Test successful password change."""
        with patch('ehp.core.services.user.AuthenticationRepository') as mock_auth_repo:
            with patch('ehp.db.db_manager.ManagedAsyncSession') as mock_session:
                mock_repo_instance = AsyncMock()
                mock_auth_repo.return_value = mock_repo_instance
                mock_repo_instance.get_by_id.return_value = mock_authentication
                mock_repo_instance.update_password.return_value = True
                
                mock_session_instance = AsyncMock()
                mock_session.return_value = mock_session_instance
                
                # Override FastAPI dependencies
                from ehp.core.services.session import get_authentication
                from ehp.base.middleware import authenticated_session
                
                test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
                test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
                
                try:
                    response = test_client.put(
                        "/users/me/password",
                        json=valid_password_change_data,
                        include_auth=True
                    )
                    
                    assert response.status_code == 200
                    response_data = response.json()
                    assert "message" in response_data
                    assert "code" in response_data
                    assert response_data["message"] == "Password updated successfully"
                    assert response_data["code"] == 200
                    
                    # Verify that the password was updated
                    mock_repo_instance.update_password.assert_called_once()
                finally:
                    test_client.app.dependency_overrides.clear()

    def test_password_change_success_and_login_with_new_password(
        self, test_client: EHPTestClient, mock_authentication, mock_user, valid_password_change_data
    ):
        """Test successful password change and then verify login with new password."""
        with patch('ehp.core.services.user.AuthenticationRepository') as mock_auth_repo:
            with patch('ehp.db.db_manager.ManagedAsyncSession') as mock_session:
                mock_repo_instance = AsyncMock()
                mock_auth_repo.return_value = mock_repo_instance
                mock_repo_instance.get_by_id.return_value = mock_authentication
                mock_repo_instance.update_password.return_value = True
                
                mock_session_instance = AsyncMock()
                mock_session.return_value = mock_session_instance
                
                # Override FastAPI dependencies
                from ehp.core.services.session import get_authentication
                from ehp.base.middleware import authenticated_session
                
                test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
                test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
                
                try:
                    # First, change the password
                    response = test_client.put(
                        "/users/me/password",
                        json=valid_password_change_data,
                        include_auth=True
                    )
                    
                    assert response.status_code == 200
                    response_data = response.json()
                    assert response_data["message"] == "Password updated successfully"
                    
                    # Verify that the password was updated
                    mock_repo_instance.update_password.assert_called_once()
                    
                    # Get the call arguments to verify the new password hash
                    call_args = mock_repo_instance.update_password.call_args
                    auth_id, new_password_hash = call_args[0]
                    
                    assert auth_id == mock_authentication.id
                    assert new_password_hash is not None
                    assert new_password_hash != mock_authentication.user_pwd
                    
                    # Test login with new password (simplified - just verify password hash would work)
                    # This verifies the password change was successful and the new hash is different
                    from ehp.utils.authentication import check_password
                    assert check_password(new_password_hash, valid_password_change_data["new_password"])
                    assert not check_password(new_password_hash, valid_password_change_data["current_password"])
                    
                finally:
                    test_client.app.dependency_overrides.clear()

    def test_password_change_authentication_not_found(
        self, test_client: EHPTestClient, mock_user
    ):
        """Test password change when authentication record is not found."""
        with patch('ehp.core.services.user.AuthenticationRepository') as mock_auth_repo:
            mock_repo_instance = AsyncMock()
            mock_auth_repo.return_value = mock_repo_instance
            mock_repo_instance.get_by_id.return_value = None
            
            # Create a mock authentication for this test
            mock_authentication = Authentication(
                id=456,
                user_email="test@example.com",
                user_name="test@example.com",
                user_pwd="hashed_password",
                is_active="1",
                is_confirmed="1"
            )
            mock_user = User(id=123, auth_id=456, full_name="Test User")
            mock_authentication.user = mock_user
            
            # Override FastAPI dependencies
            from ehp.core.services.session import get_authentication
            from ehp.base.middleware import authenticated_session
            
            test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
            test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
            
            try:
                password_data = {
                    "current_password": "CurrentPass123",
                    "new_password": "NewSecurePa$s123",
                    "confirm_password": "NewSecurePa$s123"
                }
                
                response = test_client.put(
                    "/users/me/password",
                    json=password_data,
                    include_auth=True
                )
            finally:
                test_client.app.dependency_overrides.clear()
                
                assert response.status_code == 404
                response_data = response.json()
                assert "detail" in response_data
                assert "User authentication not found" in response_data["detail"]

    def test_password_change_update_fails(
        self, test_client: EHPTestClient, mock_authentication, mock_user, valid_password_change_data
    ):
        """Test password change when password update fails."""
        with patch('ehp.core.services.user.AuthenticationRepository') as mock_auth_repo:
            mock_repo_instance = AsyncMock()
            mock_auth_repo.return_value = mock_repo_instance
            mock_repo_instance.get_by_id.return_value = mock_authentication
            mock_repo_instance.update_password.return_value = False
            
            # Override FastAPI dependencies
            from ehp.core.services.session import get_authentication
            from ehp.base.middleware import authenticated_session
            
            test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
            test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
            
            try:
                response = test_client.put(
                    "/users/me/password",
                    json=valid_password_change_data,
                    include_auth=True
                )
            finally:
                test_client.app.dependency_overrides.clear()
                
                assert response.status_code == 500
                response_data = response.json()
                assert "detail" in response_data
                assert "Failed to update password" in response_data["detail"]

    def test_password_change_database_error(
        self, test_client: EHPTestClient, mock_authentication, mock_user, valid_password_change_data
    ):
        """Test password change when database error occurs."""
        with patch('ehp.core.services.user.AuthenticationRepository') as mock_auth_repo:
            mock_repo_instance = AsyncMock()
            mock_auth_repo.return_value = mock_repo_instance
            mock_repo_instance.get_by_id.side_effect = Exception("Database error")
            
            # Override FastAPI dependencies
            from ehp.core.services.session import get_authentication
            from ehp.base.middleware import authenticated_session
            
            test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
            test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
            
            try:
                response = test_client.put(
                    "/users/me/password",
                    json=valid_password_change_data,
                    include_auth=True
                )
            finally:
                test_client.app.dependency_overrides.clear()
                
                assert response.status_code == 500
                response_data = response.json()
                assert "detail" in response_data
                assert "Internal server error" in response_data["detail"]

    def test_password_change_missing_fields(self, test_client: EHPTestClient, mock_authentication):
        """Test password change with missing required fields."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        
        # Override FastAPI dependencies
        test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
        test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
        
        try:
            incomplete_data = {
                "current_password": "CurrentPass123"
                # Missing new_password and confirm_password
            }
            
            response = test_client.put(
                "/users/me/password",
                json=incomplete_data,
                include_auth=True
            )
        finally:
            test_client.app.dependency_overrides.clear()
            
            assert response.status_code == 422
            response_data = response.json()
            assert "detail" in response_data
            # Should have validation errors for missing fields
            field_errors = [d["field"] for d in response_data["detail"] if "field" in d]
            assert "new_password" in field_errors or any("new_password" in str(d) for d in response_data["detail"])

    def test_password_change_unauthenticated(self, test_client: EHPTestClient):
        """Test password change without authentication."""
        password_data = {
            "current_password": "CurrentPass123",
            "new_password": "NewSecurePass123",
            "confirm_password": "NewSecurePass123"
        }
        
        response = test_client.put(
            "/users/me/password",
            json=password_data,
            include_auth=False  # No authentication
        )
        
        # Should return 401 or 403 depending on authentication setup
        assert response.status_code in [401, 403]
