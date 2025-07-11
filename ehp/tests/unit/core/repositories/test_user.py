from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ehp.core.models.db.user import User
from ehp.core.repositories.user import UserRepository
from ehp.utils.constants import DISPLAY_NAME_MIN_LENGTH, DISPLAY_NAME_MAX_LENGTH
from unittest.mock import AsyncMock, MagicMock

from ehp.core.repositories.user import UserNotFoundException
from ehp.core.repositories.user import InvalidNewsCategoryException


class TestUserRepository:
    """Unit tests for UserRepository."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> UserRepository:
        """Create a UserRepository instance with mocked session."""
        return UserRepository(mock_session)

    @pytest.fixture
    def sample_user(self) -> User:
        """Create a sample User instance."""
        return User(
            id=1,
            full_name="Test User",
            display_name="testuser",
            auth_id=123,
        )

    class TestGetByDisplayName:
        """Test the get_by_display_name method."""

        async def test_get_by_display_name_success(
            self, repository: UserRepository, mock_session: AsyncMock, sample_user: User
        ):
            """Test successful retrieval by display name."""
            # Arrange
            mock_session.scalar.return_value = sample_user

            # Act
            result = await repository.get_by_display_name("testuser")

            # Assert
            assert result == sample_user
            mock_session.scalar.assert_called_once()

        async def test_get_by_display_name_not_found(
            self, repository: UserRepository, mock_session: AsyncMock
        ):
            """Test when display name is not found."""
            # Arrange
            mock_session.scalar.return_value = None

            # Act
            result = await repository.get_by_display_name("nonexistent")

            # Assert
            assert result is None
            mock_session.scalar.assert_called_once()

        async def test_get_by_display_name_empty_input(
            self, repository: UserRepository, mock_session: AsyncMock
        ):
            """Test with empty display name."""
            # Act
            result = await repository.get_by_display_name("")

            # Assert
            assert result is None
            mock_session.scalar.assert_not_called()

        async def test_get_by_display_name_exception(
            self, repository: UserRepository, mock_session: AsyncMock
        ):
            """Test when an exception occurs."""
            # Arrange
            mock_session.scalar.side_effect = Exception("Database error")

            # Act
            result = await repository.get_by_display_name("testuser")

            # Assert
            assert result is None

    class TestDisplayNameExists:
        """Test the display_name_exists method."""

        async def test_display_name_exists_true(
            self, repository: UserRepository, mock_session: AsyncMock, sample_user: User
        ):
            """Test when display name exists."""
            # Arrange
            mock_session.scalar.return_value = sample_user

            # Act
            result = await repository.display_name_exists("testuser")

            # Assert
            assert result is True
            mock_session.scalar.assert_called_once()

        async def test_display_name_exists_false(
            self, repository: UserRepository, mock_session: AsyncMock
        ):
            """Test when display name doesn't exist."""
            # Arrange
            mock_session.scalar.return_value = None

            # Act
            result = await repository.display_name_exists("nonexistent")

            # Assert
            assert result is False
            mock_session.scalar.assert_called_once()

        async def test_display_name_exists_with_exclusion(
            self, repository: UserRepository, mock_session: AsyncMock
        ):
            """Test checking existence while excluding a specific user."""
            # Arrange
            mock_session.scalar.return_value = None

            # Act
            result = await repository.display_name_exists("testuser", exclude_user_id=1)

            # Assert
            assert result is False
            mock_session.scalar.assert_called_once()

        async def test_display_name_exists_empty_input(
            self, repository: UserRepository, mock_session: AsyncMock
        ):
            """Test with empty display name."""
            # Act
            result = await repository.display_name_exists("")

            # Assert
            assert result is False
            mock_session.scalar.assert_not_called()

        async def test_display_name_exists_exception(
            self, repository: UserRepository, mock_session: AsyncMock
        ):
            """Test when an exception occurs."""
            # Arrange
            mock_session.scalar.side_effect = Exception("Database error")

            # Act
            result = await repository.display_name_exists("testuser")

            # Assert
            assert result is False

    class TestInheritance:
        """Test that UserRepository properly inherits from BaseRepository."""

        def test_repository_inherits_from_base_repository(
            self, repository: UserRepository
        ):
            """Test that UserRepository inherits from BaseRepository."""
            from ehp.core.repositories.base import BaseRepository

            assert isinstance(repository, BaseRepository)

        def test_repository_has_correct_model_type(self, repository: UserRepository):
            """Test that repository has the correct model type."""
            assert repository.model == User

    @pytest.fixture
    def sample_user_avatar(self) -> User:
        """Create a sample User instance without avatar."""
        return User(
            id=123,
            auth_id=456,
            full_name="Test User",
            avatar=None  # No avatar initially
        )

    class TestUpdateAvatar:
        """Test the update_avatar method."""

        async def test_update_avatar_success(
            self, repository: UserRepository, mock_session: AsyncMock, sample_user_avatar: User
        ):
            """Test successful avatar update for user without avatar."""
            # Arrange
            avatar_url = "https://example.s3.amazonaws.com/avatars/test-avatar.png"
            
            # Mock the get_by_id method to return our sample user
            repository.get_by_id = AsyncMock(return_value=sample_user_avatar)
            
            # Act
            result = await repository.update_avatar(sample_user_avatar.id, avatar_url)
            
            # Assert
            assert result.avatar == avatar_url
            assert result.id == sample_user_avatar.id
            assert result.full_name == sample_user_avatar.full_name
            
            # Verify that get_by_id was called with correct user_id
            repository.get_by_id.assert_called_once_with(sample_user_avatar.id)
            
            # Verify that session.commit was called
            mock_session.commit.assert_called_once()

        async def test_update_avatar_user_not_found(
            self, repository: UserRepository, mock_session: AsyncMock
        ):
            """Test avatar update when user is not found."""
            # Arrange
            user_id = 999
            avatar_url = "https://example.s3.amazonaws.com/avatars/test-avatar.png"
            
            # Mock get_by_id to return None (user not found)
            repository.get_by_id = AsyncMock(return_value=None)
            
            # Act & Assert
            with pytest.raises(UserNotFoundException, match=f"User with id {user_id} not found"):
                await repository.update_avatar(user_id, avatar_url)
            
            # Verify that get_by_id was called
            repository.get_by_id.assert_called_once_with(user_id)
            
            # Verify that session.commit was not called
            mock_session.commit.assert_not_called()

        async def test_update_avatar_database_error(
            self, repository: UserRepository, mock_session: AsyncMock, sample_user_avatar: User
        ):
            """Test avatar update when database error occurs."""
            # Arrange
            avatar_url = "https://example.s3.amazonaws.com/avatars/test-avatar.png"
            
            # Mock get_by_id to return the user
            repository.get_by_id = AsyncMock(return_value=sample_user_avatar)
            
            # Mock session.commit to raise an exception
            mock_session.commit.side_effect = Exception("Database error")
            
            # Act & Assert
            with pytest.raises(Exception, match="Database error"):
                await repository.update_avatar(sample_user_avatar.id, avatar_url)
            
            # Verify that rollback was called
            mock_session.rollback.assert_called_once()

        async def test_update_avatar_replaces_existing_avatar(
            self, repository: UserRepository, mock_session: AsyncMock
        ):
            """Test avatar update replaces existing avatar."""
            # Arrange
            user_with_avatar = User(
                id=123,
                auth_id=456,
                full_name="Test User",
                avatar="https://old-avatar.com/old.png"
            )
            new_avatar_url = "https://example.s3.amazonaws.com/avatars/new-avatar.png"
            
            # Mock get_by_id to return user with existing avatar
            repository.get_by_id = AsyncMock(return_value=user_with_avatar)
            
            # Act
            result = await repository.update_avatar(user_with_avatar.id, new_avatar_url)
            
            # Assert
            assert result.avatar == new_avatar_url
            assert result.avatar != "https://old-avatar.com/old.png"
            
            # Verify session operations
            repository.get_by_id.assert_called_once_with(user_with_avatar.id)
            mock_session.commit.assert_called_once()

    class TestGetByAuthId:
        """Test the get_by_auth_id method."""

        async def test_get_by_auth_id_success(
            self, repository: UserRepository, mock_session: AsyncMock, sample_user: User
        ):
            """Test successful get user by auth_id."""
            # Arrange
            auth_id = 456
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = sample_user
            mock_session.execute.return_value = mock_result
            
            # Act
            result = await repository.get_by_auth_id(auth_id)
            
            # Assert
            assert result == sample_user
            mock_session.execute.assert_called_once()

        async def test_get_by_auth_id_not_found(
            self, repository: UserRepository, mock_session: AsyncMock
        ):
            """Test get user by auth_id when user not found."""
            # Arrange
            auth_id = 999
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result
            
            # Act
            result = await repository.get_by_auth_id(auth_id)
            
            # Assert
            assert result is None
            mock_session.execute.assert_called_once()

    class TestUpdateFullName:
        """Test the update_full_name method."""

        async def test_update_full_name_success(
            self, repository: UserRepository, mock_session: AsyncMock, sample_user: User
        ):
            """Test successful full name update."""
            # Arrange
            new_name = "Updated Name"
            repository.get_by_id = AsyncMock(return_value=sample_user)
            
            # Act
            result = await repository.update_full_name(sample_user.id, new_name)
            
            # Assert
            assert result.full_name == new_name
            assert result.id == sample_user.id
            repository.get_by_id.assert_called_once_with(sample_user.id)
            mock_session.commit.assert_called_once()

        async def test_update_full_name_user_not_found(
            self, repository: UserRepository, mock_session: AsyncMock
        ):
            """Test full name update when user not found."""
            # Arrange
            user_id = 999
            new_name = "Updated Name"
            repository.get_by_id = AsyncMock(return_value=None)
            
            # Act & Assert
            with pytest.raises(UserNotFoundException, match=f"User with id {user_id} not found"):
                await repository.update_full_name(user_id, new_name)
            
            repository.get_by_id.assert_called_once_with(user_id)
            mock_session.commit.assert_not_called()

        async def test_update_full_name_database_error(
            self, repository: UserRepository, mock_session: AsyncMock, sample_user: User
        ):
            """Test full name update when database error occurs."""
            # Arrange
            new_name = "Updated Name"
            repository.get_by_id = AsyncMock(return_value=sample_user)
            mock_session.commit.side_effect = Exception("Database error")
            
            # Act & Assert
            with pytest.raises(Exception, match="Database error"):
                await repository.update_full_name(sample_user.id, new_name)
            
            mock_session.rollback.assert_called_once()

    class TestUpdatePreferredNewsCategories:
        """Test the update_preferred_news_categories method."""

        async def test_update_preferred_news_categories_success(
            self, repository: UserRepository, mock_session: AsyncMock, sample_user: User
        ):
            """Test successful news categories update."""
            # Arrange
            category_ids = [1, 2, 3]
            
            # Mock category validation query
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [(1,), (2,), (3,)]
            mock_session.execute.return_value = mock_result
            
            repository.get_by_id = AsyncMock(return_value=sample_user)
            
            # Act
            result = await repository.update_preferred_news_categories(sample_user.id, category_ids)
            
            # Assert
            assert result.preferred_news_categories == category_ids
            repository.get_by_id.assert_called_once_with(sample_user.id)
            mock_session.commit.assert_called_once()

        async def test_update_preferred_news_categories_empty_list(
            self, repository: UserRepository, mock_session: AsyncMock, sample_user: User
        ):
            """Test news categories update with empty list."""
            # Arrange
            category_ids = []
            repository.get_by_id = AsyncMock(return_value=sample_user)
            
            # Act
            result = await repository.update_preferred_news_categories(sample_user.id, category_ids)
            
            # Assert
            assert result.preferred_news_categories is None
            repository.get_by_id.assert_called_once_with(sample_user.id)
            mock_session.commit.assert_called_once()

        async def test_update_preferred_news_categories_invalid_category(
            self, repository: UserRepository, mock_session: AsyncMock, sample_user: User
        ):
            """Test news categories update with invalid category."""
            # Arrange
            category_ids = [1, 2, 999]  # 999 doesn't exist
            
            # Mock category validation query - only return 1 and 2
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [(1,), (2,)]
            mock_session.execute.return_value = mock_result
            
            # Act & Assert
            with pytest.raises(InvalidNewsCategoryException):
                await repository.update_preferred_news_categories(sample_user.id, category_ids)

        async def test_update_preferred_news_categories_user_not_found(
            self, repository: UserRepository, mock_session: AsyncMock
        ):
            """Test news categories update when user not found."""
            # Arrange
            user_id = 999
            category_ids = [1, 2, 3]
            
            # Mock category validation query
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [(1,), (2,), (3,)]
            mock_session.execute.return_value = mock_result
            
            repository.get_by_id = AsyncMock(return_value=None)
            
            # Act & Assert
            with pytest.raises(UserNotFoundException, match=f"User with id {user_id} not found"):
                await repository.update_preferred_news_categories(user_id, category_ids)
            
            repository.get_by_id.assert_called_once_with(user_id)
            mock_session.commit.assert_not_called()

        async def test_update_preferred_news_categories_database_error(
            self, repository: UserRepository, mock_session: AsyncMock, sample_user: User
        ):
            """Test news categories update when database error occurs."""
            # Arrange
            category_ids = [1, 2, 3]
            
            # Mock category validation query
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [(1,), (2,), (3,)]
            mock_session.execute.return_value = mock_result
            
            repository.get_by_id = AsyncMock(return_value=sample_user)
            mock_session.commit.side_effect = Exception("Database error")
            
            # Act & Assert
            with pytest.raises(Exception, match="Database error"):
                await repository.update_preferred_news_categories(sample_user.id, category_ids)
            
            mock_session.rollback.assert_called_once()
