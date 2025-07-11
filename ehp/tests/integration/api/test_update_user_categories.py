import pytest
from unittest.mock import patch, AsyncMock

from ehp.core.models.db.authentication import Authentication
from ehp.core.models.db.user import User
from ehp.core.models.db.news_category import NewsCategory
from ehp.tests.utils.test_client import EHPTestClient
from ehp.utils.authentication import hash_password


@pytest.mark.integration
class TestUpdateUserCategoriesEndpoint:
    """Integration tests for the /users/me/settings/categories endpoint."""

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
        """Mock user record without preferred categories."""
        return User(
            id=valid_user_data["user_id"],
            auth_id=valid_user_data["auth_id"],
            full_name=valid_user_data["full_name"],
            preferred_news_categories=None
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
    def mock_news_categories(self):
        """Mock news categories."""
        return [
            NewsCategory(id=1, name="Technology"),
            NewsCategory(id=2, name="Politics"),
            NewsCategory(id=3, name="Sports"),
            NewsCategory(id=4, name="Entertainment"),
            NewsCategory(id=5, name="Health"),
            NewsCategory(id=6, name="Science"),
            NewsCategory(id=7, name="Business"),
            NewsCategory(id=8, name="World News"),
            NewsCategory(id=9, name="Environment"),
            NewsCategory(id=10, name="Education"),
        ]

    def test_update_user_categories_success(
        self, test_client: EHPTestClient, mock_authentication, mock_user, mock_news_categories
    ):
        """Test successful update of user preferred categories."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        
        # Mock user repository
        with patch('ehp.core.services.user.UserRepository') as mock_user_repo:
            with patch('ehp.db.db_manager.ManagedAsyncSession'):
                mock_repo_instance = AsyncMock()
                mock_user_repo.return_value = mock_repo_instance
                
                # Mock user with updated categories
                updated_user = User(
                    id=mock_user.id,
                    auth_id=mock_user.auth_id,
                    full_name=mock_user.full_name,
                    preferred_news_categories=[1, 3, 5]
                )
                mock_repo_instance.update_preferred_news_categories.return_value = updated_user
                
                # Override FastAPI dependencies
                test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
                test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
                
                try:
                    categories_data = {
                        "category_ids": [1, 3, 5]
                    }
                    
                    response = test_client.put(
                        "/users/me/settings/categories",
                        json=categories_data,
                        include_auth=True
                    )
                    
                    assert response.status_code == 200
                    response_data = response.json()
                    assert "id" in response_data
                    assert "full_name" in response_data
                    assert "preferred_news_categories" in response_data
                    assert response_data["id"] == mock_user.id
                    assert response_data["full_name"] == mock_user.full_name
                    assert response_data["preferred_news_categories"] == [1, 3, 5]
                    
                    # Verify repository method was called with correct arguments
                    mock_repo_instance.update_preferred_news_categories.assert_called_once_with(
                        mock_user.id, [1, 3, 5]
                    )
                    
                finally:
                    test_client.app.dependency_overrides.clear()

    def test_update_user_categories_empty_list(
        self, test_client: EHPTestClient, mock_authentication, mock_user
    ):
        """Test update with empty category list."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        
        with patch('ehp.core.services.user.UserRepository') as mock_user_repo:
            with patch('ehp.db.db_manager.ManagedAsyncSession'):
                mock_repo_instance = AsyncMock()
                mock_user_repo.return_value = mock_repo_instance
                
                # Mock user with no categories
                updated_user = User(
                    id=mock_user.id,
                    auth_id=mock_user.auth_id,
                    full_name=mock_user.full_name,
                    preferred_news_categories=None
                )
                mock_repo_instance.update_preferred_news_categories.return_value = updated_user
                
                # Override FastAPI dependencies
                test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
                test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
                
                try:
                    categories_data = {
                        "category_ids": []
                    }
                    
                    response = test_client.put(
                        "/users/me/settings/categories",
                        json=categories_data,
                        include_auth=True
                    )
                    
                    assert response.status_code == 200
                    response_data = response.json()
                    assert response_data["preferred_news_categories"] is None
                    
                    # Verify repository method was called with empty list
                    mock_repo_instance.update_preferred_news_categories.assert_called_once_with(
                        mock_user.id, []
                    )
                    
                finally:
                    test_client.app.dependency_overrides.clear()

    def test_update_user_categories_duplicate_removal(
        self, test_client: EHPTestClient, mock_authentication, mock_user
    ):
        """Test that duplicate category IDs are removed."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        
        with patch('ehp.core.services.user.UserRepository') as mock_user_repo:
            with patch('ehp.db.db_manager.ManagedAsyncSession'):
                mock_repo_instance = AsyncMock()
                mock_user_repo.return_value = mock_repo_instance
                
                # Mock user with deduplicated categories
                updated_user = User(
                    id=mock_user.id,
                    auth_id=mock_user.auth_id,
                    full_name=mock_user.full_name,
                    preferred_news_categories=[1, 3, 5]
                )
                mock_repo_instance.update_preferred_news_categories.return_value = updated_user
                
                # Override FastAPI dependencies
                test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
                test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
                
                try:
                    # Send duplicate category IDs
                    categories_data = {
                        "category_ids": [1, 3, 5, 1, 3]  # Duplicates: 1 and 3
                    }
                    
                    response = test_client.put(
                        "/users/me/settings/categories",
                        json=categories_data,
                        include_auth=True
                    )
                    
                    assert response.status_code == 200
                    
                    # Verify repository was called with deduplicated list
                    mock_repo_instance.update_preferred_news_categories.assert_called_once_with(
                        mock_user.id, [1, 3, 5]  # No duplicates
                    )
                    
                finally:
                    test_client.app.dependency_overrides.clear()

    def test_update_user_categories_invalid_category_ids(
        self, test_client: EHPTestClient, mock_authentication, mock_user
    ):
        """Test update with invalid category IDs."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        from ehp.core.repositories.user import InvalidNewsCategoryException
        
        with patch('ehp.core.services.user.UserRepository') as mock_user_repo:
            with patch('ehp.db.db_manager.ManagedAsyncSession'):
                mock_repo_instance = AsyncMock()
                mock_user_repo.return_value = mock_repo_instance
                
                # Mock repository to raise InvalidNewsCategoryException
                mock_repo_instance.update_preferred_news_categories.side_effect = InvalidNewsCategoryException(
                    "Invalid news category IDs: [999, 1000]"
                )
                
                # Override FastAPI dependencies
                test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
                test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
                
                try:
                    categories_data = {
                        "category_ids": [999, 1000]  # Non-existent category IDs
                    }
                    
                    response = test_client.put(
                        "/users/me/settings/categories",
                        json=categories_data,
                        include_auth=True
                    )
                    
                    assert response.status_code == 400
                    response_data = response.json()
                    assert "detail" in response_data
                    assert "Invalid news category IDs: [999, 1000]" in response_data["detail"]
                    
                finally:
                    test_client.app.dependency_overrides.clear()

    def test_update_user_categories_user_not_found(
        self, test_client: EHPTestClient, mock_authentication
    ):
        """Test update when user is not found."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        from ehp.core.repositories.user import UserNotFoundException
        
        with patch('ehp.core.services.user.UserRepository') as mock_user_repo:
            with patch('ehp.db.db_manager.ManagedAsyncSession'):
                mock_repo_instance = AsyncMock()
                mock_user_repo.return_value = mock_repo_instance
                
                # Mock repository to raise UserNotFoundException
                mock_repo_instance.update_preferred_news_categories.side_effect = UserNotFoundException(
                    "User with id 123 not found"
                )
                
                # Override FastAPI dependencies
                test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
                test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
                
                try:
                    categories_data = {
                        "category_ids": [1, 2, 3]
                    }
                    
                    response = test_client.put(
                        "/users/me/settings/categories",
                        json=categories_data,
                        include_auth=True
                    )
                    
                    assert response.status_code == 404
                    response_data = response.json()
                    assert "detail" in response_data
                    assert "User not found" in response_data["detail"]
                    
                finally:
                    test_client.app.dependency_overrides.clear()

    def test_update_user_categories_unauthenticated(self, test_client: EHPTestClient):
        """Test update without authentication."""
        categories_data = {
            "category_ids": [1, 2, 3]
        }
        
        response = test_client.put(
            "/users/me/settings/categories",
            json=categories_data,
            include_auth=False
        )
        
        # Should return 401 or 403 depending on authentication setup
        assert response.status_code in [401, 403]

    def test_update_user_categories_invalid_payload(
        self, test_client: EHPTestClient, mock_authentication
    ):
        """Test update with invalid payload structure."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        
        # Override FastAPI dependencies
        test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
        test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
        
        try:
            # Missing required field
            invalid_data = {
                "wrong_field": [1, 2, 3]
            }
            
            response = test_client.put(
                "/users/me/settings/categories",
                json=invalid_data,
                include_auth=True
            )
            
            assert response.status_code == 422
            response_data = response.json()
            assert "detail" in response_data
            
        finally:
            test_client.app.dependency_overrides.clear()

    def test_update_user_categories_non_list_category_ids(
        self, test_client: EHPTestClient, mock_authentication
    ):
        """Test update with non-list category_ids."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        
        # Override FastAPI dependencies
        test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
        test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
        
        try:
            # category_ids should be a list, not a string
            invalid_data = {
                "category_ids": "not a list"
            }
            
            response = test_client.put(
                "/users/me/settings/categories",
                json=invalid_data,
                include_auth=True
            )
            
            assert response.status_code == 422
            response_data = response.json()
            assert "detail" in response_data
            
        finally:
            test_client.app.dependency_overrides.clear()

    def test_update_user_categories_database_error(
        self, test_client: EHPTestClient, mock_authentication, mock_user
    ):
        """Test update when database error occurs."""
        from ehp.core.services.session import get_authentication
        from ehp.base.middleware import authenticated_session
        
        with patch('ehp.core.services.user.UserRepository') as mock_user_repo:
            with patch('ehp.db.db_manager.ManagedAsyncSession'):
                mock_repo_instance = AsyncMock()
                mock_user_repo.return_value = mock_repo_instance
                
                # Mock repository to raise a general exception
                mock_repo_instance.update_preferred_news_categories.side_effect = Exception("Database connection error")
                
                # Override FastAPI dependencies
                test_client.app.dependency_overrides[authenticated_session] = lambda: {"sub": str(mock_authentication.id)}
                test_client.app.dependency_overrides[get_authentication] = lambda: mock_authentication
                
                try:
                    categories_data = {
                        "category_ids": [1, 2, 3]
                    }
                    
                    response = test_client.put(
                        "/users/me/settings/categories",
                        json=categories_data,
                        include_auth=True
                    )
                    
                    assert response.status_code == 500
                    response_data = response.json()
                    assert "detail" in response_data
                    assert "Internal server error" in response_data["detail"]
                    
                finally:
                    test_client.app.dependency_overrides.clear()
