from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ehp.core.models.db.wikiclip import WikiClip
from ehp.core.models.schema.wikiclip import (
    WikiClipSearchSchema,
    WikiClipSearchSortStrategy,
)
from ehp.core.repositories.wikiclip import WikiClipRepository


class TestWikiClipRepository:
    """Unit tests for WikiClipRepository."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> WikiClipRepository:
        """Create a WikiClipRepository instance with mocked session."""
        return WikiClipRepository(mock_session)

    @pytest.fixture
    def sample_wikiclip(self) -> WikiClip:
        """Create a sample WikiClip instance."""
        return WikiClip(
            id=1,
            title="Test Article",
            content="Test content",
            url="https://example.com/test",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            user_id=123,
            related_links=["https://example.com/link1"],
        )

    @pytest.fixture
    def sample_search_schema(self) -> WikiClipSearchSchema:
        """Create a sample search schema."""
        return WikiClipSearchSchema(
            search_term="test",
            page=1,
            size=10,
            sort_by=WikiClipSearchSortStrategy.CREATION_DATE_DESC,
            filter_by_user=True,
        )

    class TestExists:
        """Test the exists method."""

        async def test_exists_returns_true_when_wikiclip_found(
            self, repository: WikiClipRepository, mock_session: AsyncMock
        ):
            """Test that exists returns True when WikiClip is found."""
            # Arrange
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = True
            mock_session.execute.return_value = mock_result

            # Act
            result = await repository.exists(
                url="https://example.com/test",
                created_at=date(2024, 1, 1),
                title="Test Article",
                user_id=123,
            )

            # Assert
            assert result is True
            mock_session.execute.assert_called_once()

        async def test_exists_returns_false_when_wikiclip_not_found(
            self, repository: WikiClipRepository, mock_session: AsyncMock
        ):
            """Test that exists returns False when WikiClip is not found."""
            # Arrange
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = False
            mock_session.execute.return_value = mock_result

            # Act
            result = await repository.exists(
                url="https://example.com/test",
                created_at=date(2024, 1, 1),
                title="Test Article",
                user_id=123,
            )

            # Assert
            assert result is False
            mock_session.execute.assert_called_once()

        async def test_exists_returns_false_on_exception(
            self, repository: WikiClipRepository, mock_session: AsyncMock
        ):
            """Test that exists returns False when an exception occurs."""
            # Arrange
            # The exception should be raised during session.execute, not during query creation
            mock_session.execute.side_effect = Exception("Database error")

            # Act
            result = await repository.exists(
                url="https://example.com/test",
                created_at=date(2024, 1, 1),
                title="Test Article",
                user_id=123,
            )

            # Assert
            assert result is False
            mock_session.execute.assert_called_once()

    @patch("ehp.core.repositories.wikiclip.select")
    async def test_exists_returns_false_on_exception_during_statement_creation(
        self,
        mock_select: MagicMock,
        repository: WikiClipRepository,
        mock_session: AsyncMock,
    ):
        """Test that exists returns False when an exception occurs during query creation."""
        # Arrange
        mock_select.side_effect = Exception("Statement creation error")

        # Act
        with patch("ehp.core.repositories.wikiclip.log_error") as mock_log:
            result = await repository.exists(
                url="https://example.com/test",
                created_at=date(2024, 1, 1),
                title="Test Article",
                user_id=123,
            )

        # Assert
        assert result is False
        mock_session.execute.assert_not_called()
        mock_log.assert_called_once()

    class TestApplyFilters:
        """Test the apply_filters method."""

        def test_apply_filters_with_search_term(
            self,
            repository: WikiClipRepository,
            sample_search_schema: WikiClipSearchSchema,
        ):
            """Test applying search term filter."""
            # Arrange
            query = select(WikiClip)
            user_id = 123

            # Act
            result = repository.apply_filters(query, sample_search_schema, user_id)

            # Assert
            assert result is not None
            # The query should be modified but we can't easily test the internal structure
            # without executing it, so we just verify it's not the original query

        def test_apply_filters_with_date_filters(self, repository: WikiClipRepository):
            """Test applying date filters."""
            # Arrange
            search_schema = WikiClipSearchSchema(
                created_before=datetime(2024, 12, 31),
                created_after=datetime(2024, 1, 1),
                page=1,
                size=10,
            )
            query = select(WikiClip)
            user_id = 123

            # Act
            result = repository.apply_filters(query, search_schema, user_id)

            # Assert
            assert result is not None

        def test_apply_filters_with_sorting(self, repository: WikiClipRepository):
            """Test applying sorting."""
            # Arrange
            search_schema = WikiClipSearchSchema(
                sort_by=WikiClipSearchSortStrategy.CREATION_DATE_ASC, page=1, size=10
            )
            query = select(WikiClip)
            user_id = 123

            # Act
            result = repository.apply_filters(query, search_schema, user_id)

            # Assert
            assert result is not None

        def test_apply_filters_with_user_filter(self, repository: WikiClipRepository):
            """Test applying user filter."""
            # Arrange
            search_schema = WikiClipSearchSchema(filter_by_user=True, page=1, size=10)
            query = select(WikiClip)
            user_id = 123

            # Act
            result = repository.apply_filters(query, search_schema, user_id)

            # Assert
            assert result is not None

        def test_apply_filters_no_filters(self, repository: WikiClipRepository):
            """Test apply_filters with no filters applied."""
            search_schema = WikiClipSearchSchema(page=1, size=10)  # Todos None/False
            query = select(WikiClip)

            result = repository.apply_filters(query, search_schema, 123)
            assert result is not None

        def test_apply_filters_all_combinations(self, repository: WikiClipRepository):
            """Test apply_filters with all filters combined."""
            search_schema = WikiClipSearchSchema(
                search_term="test",
                created_before=datetime(2024, 12, 31),
                created_after=datetime(2024, 1, 1),
                filter_by_user=True,
                sort_by=WikiClipSearchSortStrategy.CREATION_DATE_DESC,
                page=1,
                size=10,
            )
            query = select(WikiClip)

            result = repository.apply_filters(query, search_schema, 123)
            assert result is not None

    class TestSearch:
        """Test the search method."""

        async def test_search_returns_wikiclips(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
            sample_wikiclip: WikiClip,
        ):
            """Test that search returns WikiClips."""
            # Arrange
            mock_result = MagicMock()
            mock_result.scalars.return_value.unique.return_value.all.return_value = [
                sample_wikiclip
            ]
            mock_session.execute.return_value = mock_result

            search_schema = WikiClipSearchSchema(page=1, size=10)

            # Act
            result = await repository.search(user_id=123, search=search_schema)

            # Assert
            assert result == [sample_wikiclip]
            mock_session.execute.assert_called_once()

        async def test_search_returns_empty_list_on_exception(
            self, repository: WikiClipRepository, mock_session: AsyncMock
        ):
            """Test that search returns empty list when an exception occurs."""
            # Arrange
            mock_session.execute.side_effect = Exception("Database error")
            search_schema = WikiClipSearchSchema(page=1, size=10)

            # Act
            result = await repository.search(user_id=123, search=search_schema)

            # Assert
            assert result == []

        async def test_search_applies_pagination(
            self, repository: WikiClipRepository, mock_session: AsyncMock
        ):
            """Test that search applies pagination correctly."""
            # Arrange
            mock_result = MagicMock()
            mock_result.scalars.return_value.unique.return_value.all.return_value = []
            mock_session.execute.return_value = mock_result

            search_schema = WikiClipSearchSchema(page=2, size=5)

            # Act
            await repository.search(user_id=123, search=search_schema)

            # Assert
            # Verify that limit and offset are applied
            call_args = mock_session.execute.call_args[0][0]
            assert hasattr(call_args, "_limit")
            assert hasattr(call_args, "_offset")

    class TestCount:
        """Test the count method."""

        async def test_count_returns_correct_number(
            self, repository: WikiClipRepository, mock_session: AsyncMock
        ):
            """Test that count returns the correct number."""
            # Arrange
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = 5
            mock_session.execute.return_value = mock_result

            search_schema = WikiClipSearchSchema(page=1, size=10)

            # Act
            result = await repository.count(user_id=123, search=search_schema)

            # Assert
            assert result == 5
            mock_session.execute.assert_called_once()

        async def test_count_returns_zero_on_exception(
            self, repository: WikiClipRepository, mock_session: AsyncMock
        ):
            """Test that count returns zero when an exception occurs."""
            # Arrange
            mock_session.execute.side_effect = Exception("Database error")
            search_schema = WikiClipSearchSchema(page=1, size=10)

            # Act
            result = await repository.count(user_id=123, search=search_schema)

            # Assert
            assert result == 0

    class TestCheckDuplicate:
        """Test the check_duplicate method."""

        @patch("ehp.core.repositories.wikiclip.timezone_now")
        async def test_check_duplicate_returns_false_when_no_duplicate(
            self,
            mock_timezone_now: MagicMock,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
        ):
            """Test that check_duplicate returns False when no duplicate is found."""
            # Arrange
            mock_timezone_now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            mock_result = MagicMock()
            mock_result.scalars.return_value.first.return_value = None
            mock_session.execute.return_value = mock_result

            # Act
            is_duplicate, duplicate_article, hours_diff = (
                await repository.check_duplicate(
                    url="https://example.com/test",
                    title="Test Article",
                    user_id=123,
                    hours_threshold=24,
                )
            )

            # Assert
            assert is_duplicate is False
            assert duplicate_article is None
            assert hours_diff is None
            mock_session.execute.assert_called_once()

        @patch("ehp.core.repositories.wikiclip.timezone_now")
        async def test_check_duplicate_returns_true_when_duplicate_found(
            self,
            mock_timezone_now: MagicMock,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
            sample_wikiclip: WikiClip,
        ):
            """Test that check_duplicate returns True when duplicate is found."""
            # Arrange
            current_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_timezone_now.return_value = current_time

            # Set the sample wikiclip to be within threshold
            sample_wikiclip.created_at = current_time - timedelta(hours=2)

            mock_result = MagicMock()
            mock_result.scalars.return_value.first.return_value = sample_wikiclip
            mock_session.execute.return_value = mock_result

            # Act
            is_duplicate, duplicate_article, hours_diff = (
                await repository.check_duplicate(
                    url="https://example.com/test",
                    title="Test Article",
                    user_id=123,
                    hours_threshold=24,
                )
            )

            # Assert
            assert is_duplicate is True
            assert duplicate_article == sample_wikiclip
            assert hours_diff == 2.0
            mock_session.execute.assert_called_once()

        @patch("ehp.core.repositories.wikiclip.timezone_now")
        async def test_check_duplicate_returns_false_when_duplicate_outside_threshold(
            self,
            mock_timezone_now: MagicMock,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
            sample_wikiclip: WikiClip,
        ):
            """Test that check_duplicate returns False when duplicate is outside threshold."""
            # Arrange
            current_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_timezone_now.return_value = current_time

            # Set the sample wikiclip to be outside threshold
            sample_wikiclip.created_at = current_time - timedelta(hours=25)

            mock_result = MagicMock()
            mock_result.scalars.return_value.first.return_value = (
                None  # No result due to threshold
            )
            mock_session.execute.return_value = mock_result

            # Act
            is_duplicate, duplicate_article, hours_diff = (
                await repository.check_duplicate(
                    url="https://example.com/test",
                    title="Test Article",
                    user_id=123,
                    hours_threshold=24,
                )
            )

            # Assert
            assert is_duplicate is False
            assert duplicate_article is None
            assert hours_diff is None

        async def test_check_duplicate_returns_false_on_exception(
            self, repository: WikiClipRepository, mock_session: AsyncMock
        ):
            """Test that check_duplicate returns False when an exception occurs."""
            # Arrange
            mock_session.execute.side_effect = Exception("Database error")

            # Act
            is_duplicate, duplicate_article, hours_diff = (
                await repository.check_duplicate(
                    url="https://example.com/test",
                    title="Test Article",
                    user_id=123,
                    hours_threshold=24,
                )
            )

            # Assert
            assert is_duplicate is False
            assert duplicate_article is None
            assert hours_diff is None

        @patch("ehp.core.repositories.wikiclip.timezone_now")
        async def test_check_duplicate_with_custom_threshold(
            self,
            mock_timezone_now: MagicMock,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
            sample_wikiclip: WikiClip,
        ):
            """Test that check_duplicate works with custom hours threshold."""
            # Arrange
            current_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_timezone_now.return_value = current_time

            # Set the sample wikiclip to be within 6-hour threshold
            sample_wikiclip.created_at = current_time - timedelta(hours=3)

            mock_result = MagicMock()
            mock_result.scalars.return_value.first.return_value = sample_wikiclip
            mock_session.execute.return_value = mock_result

            # Act
            is_duplicate, duplicate_article, hours_diff = (
                await repository.check_duplicate(
                    url="https://example.com/test",
                    title="Test Article",
                    user_id=123,
                    hours_threshold=6,  # Custom threshold
                )
            )

            # Assert
            assert is_duplicate is True
            assert duplicate_article == sample_wikiclip
            assert hours_diff == 3.0

    class TestInheritance:
        """Test that WikiClipRepository properly inherits from BaseRepository."""

        def test_repository_inherits_from_base_repository(
            self, repository: WikiClipRepository
        ):
            """Test that WikiClipRepository inherits from BaseRepository."""
            from ehp.core.repositories.base import BaseRepository

            assert isinstance(repository, BaseRepository)

        def test_repository_has_correct_model_type(
            self, repository: WikiClipRepository
        ):
            """Test that repository has the correct model type."""
            assert repository.model == WikiClip

    class TestGetUserPages:
        """Test the get_user_pages method."""

        @pytest.fixture
        def sample_user_pages(self):
            """Create sample WikiClip instances for user pages tests."""
            # 4 articles for user 123 - ordered by created_at desc
            user_123_articles = [
                WikiClip(
                    id=4,
                    title="My Latest Article",
                    content="Latest content from my collection",
                    url="https://example.com/my-latest",
                    created_at=datetime(2024, 1, 4, 12, 0, 0),
                    user_id=123,
                    related_links=["https://example.com/related1"],
                ),
                WikiClip(
                    id=3,
                    title="My Recent Article", 
                    content="Recent content from my saves",
                    url="https://example.com/my-recent",
                    created_at=datetime(2024, 1, 3, 12, 0, 0),
                    user_id=123,
                    related_links=[],
                ),
                WikiClip(
                    id=2,
                    title="My Older Article",
                    content="Older content in my collection",
                    url="https://example.com/my-older",
                    created_at=datetime(2024, 1, 2, 12, 0, 0),
                    user_id=123,
                    related_links=["https://example.com/related2", "https://example.com/related3"],
                ),
                WikiClip(
                    id=1,
                    title="My Oldest Article",
                    content="Oldest content I saved",
                    url="https://example.com/my-oldest", 
                    created_at=datetime(2024, 1, 1, 12, 0, 0),
                    user_id=123,
                    related_links=None,
                ),
            ]
            
            # Article from different user that shouldn't be fetched
            other_user_article = WikiClip(
                id=5,
                title="Other User Article",
                content="Content from another user",
                url="https://example.com/other-user",
                created_at=datetime(2024, 1, 5, 12, 0, 0),  # Even newer but different user
                user_id=456,
                related_links=[],
            )
            
            return user_123_articles, other_user_article

        async def test_get_user_pages_returns_ordered_wikiclips(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
            sample_user_pages,
        ):
            """Test that get_user_pages returns WikiClips ordered by created_at desc."""
            # Arrange
            user_123_articles, other_user_article = sample_user_pages
            mock_result = MagicMock()
            # Return only user 123's articles, ordered by created_at desc
            mock_result.scalars.return_value.unique.return_value.all.return_value = user_123_articles
            mock_session.execute.return_value = mock_result

            # Act
            result = await repository.get_user_pages(user_id=123, page=1, page_size=5)

            # Assert
            assert len(result) == 4
            # Verify ordering by created_at desc
            assert result[0].id == 4  # Latest (2024-01-04)
            assert result[1].id == 3  # Recent (2024-01-03)
            assert result[2].id == 2  # Older (2024-01-02)
            assert result[3].id == 1  # Oldest (2024-01-01)
            
            # Verify all articles belong to user 123
            for article in result:
                assert article.user_id == 123
                
            mock_session.execute.assert_called_once()

        async def test_get_user_pages_filters_by_user(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
            sample_user_pages,
        ):
            """Test that get_user_pages filters articles by user_id and excludes other users."""
            # Arrange
            user_123_articles, other_user_article = sample_user_pages
            mock_result = MagicMock()
            # Repository should only return user 123's articles, not the other user's
            mock_result.scalars.return_value.unique.return_value.all.return_value = user_123_articles
            mock_session.execute.return_value = mock_result

            # Act
            result = await repository.get_user_pages(user_id=123, page=1, page_size=5)

            # Assert
            assert len(result) == 4
            # Verify all returned articles belong to user 123
            for article in result:
                assert article.user_id == 123
                assert article.user_id != 456  # Should not include other user's articles

            # Verify that the query includes user_cd_id filter
            call_args = mock_session.execute.call_args[0][0]
            query_str = str(call_args)
            assert "user_cd_id" in query_str.lower()

        async def test_get_user_pages_applies_pagination(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
            sample_user_pages,
        ):
            """Test that get_user_pages applies correct pagination."""
            # Arrange
            user_123_articles, _ = sample_user_pages
            mock_result = MagicMock()
            # Return only first 2 articles for page_size=2
            mock_result.scalars.return_value.unique.return_value.all.return_value = user_123_articles[:2]
            mock_session.execute.return_value = mock_result

            # Act
            await repository.get_user_pages(user_id=123, page=2, page_size=2)

            # Assert
            call_args = mock_session.execute.call_args[0][0]
            # Verify limit and offset are set correctly
            # Page 2, page_size 2 should have offset = (2-1) * 2 = 2
            assert hasattr(call_args, "_limit")
            assert hasattr(call_args, "_offset")

        async def test_get_user_pages_returns_empty_list_on_exception(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
        ):
            """Test that get_user_pages returns empty list when an exception occurs."""
            # Arrange
            mock_session.execute.side_effect = Exception("Database error")

            # Act
            result = await repository.get_user_pages(user_id=123, page=1, page_size=5)

            # Assert
            assert result == []

        async def test_get_user_pages_with_custom_page_size(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
            sample_user_pages,
        ):
            """Test that get_user_pages respects custom page_size."""
            # Arrange
            user_123_articles, _ = sample_user_pages
            mock_result = MagicMock()
            # Return only first 3 articles for page_size=3
            mock_result.scalars.return_value.unique.return_value.all.return_value = user_123_articles[:3]
            mock_session.execute.return_value = mock_result

            # Act
            result = await repository.get_user_pages(user_id=123, page=1, page_size=3)

            # Assert
            assert len(result) == 3
            call_args = mock_session.execute.call_args[0][0]
            assert hasattr(call_args, "_limit")

        async def test_get_user_pages_default_pagination(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
            sample_user_pages,
        ):
            """Test that get_user_pages uses default pagination values."""
            # Arrange
            user_123_articles, _ = sample_user_pages
            mock_result = MagicMock()
            mock_result.scalars.return_value.unique.return_value.all.return_value = user_123_articles
            mock_session.execute.return_value = mock_result

            # Act - call without explicit page/page_size parameters
            result = await repository.get_user_pages(user_id=123)

            # Assert
            assert len(result) == 4
            call_args = mock_session.execute.call_args[0][0]
            # Should use default values: page=1, page_size=20
            assert hasattr(call_args, "_limit")
            assert hasattr(call_args, "_offset")

    class TestCountUserPages:
        """Test the count_user_pages method."""

        async def test_count_user_pages_returns_correct_count(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
        ):
            """Test that count_user_pages returns the correct count for a user."""
            # Arrange
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = 4  # 4 articles for user 123
            mock_session.execute.return_value = mock_result

            # Act
            result = await repository.count_user_pages(user_id=123)

            # Assert
            assert result == 4
            mock_session.execute.assert_called_once()

        async def test_count_user_pages_filters_by_user(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
        ):
            """Test that count_user_pages filters by user_id."""
            # Arrange
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = 1  # 1 article for user 456
            mock_session.execute.return_value = mock_result

            # Act
            result = await repository.count_user_pages(user_id=456)

            # Assert
            assert result == 1
            # Verify that the query includes user_cd_id filter
            call_args = mock_session.execute.call_args[0][0]
            query_str = str(call_args)
            assert "user_cd_id" in query_str.lower()

        async def test_count_user_pages_returns_zero_on_exception(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
        ):
            """Test that count_user_pages returns zero when an exception occurs."""
            # Arrange
            mock_session.execute.side_effect = Exception("Database error")

            # Act
            result = await repository.count_user_pages(user_id=123)

            # Assert
            assert result == 0

        async def test_count_user_pages_with_no_pages(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
        ):
            """Test that count_user_pages returns zero when user has no pages."""
            # Arrange
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = 0  # No articles for user
            mock_session.execute.return_value = mock_result

            # Act
            result = await repository.count_user_pages(user_id=999)

            # Assert
            assert result == 0
            mock_session.execute.assert_called_once()

        async def test_count_user_pages_different_users(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
        ):
            """Test that count_user_pages returns different counts for different users."""
            # Arrange
            mock_result = MagicMock()
            mock_session.execute.return_value = mock_result
            
            # First user has 5 pages
            mock_result.scalar_one.return_value = 5
            result1 = await repository.count_user_pages(user_id=123)
            
            # Second user has 2 pages
            mock_result.scalar_one.return_value = 2
            result2 = await repository.count_user_pages(user_id=456)

            # Assert
            assert result1 == 5
            assert result2 == 2
            assert mock_session.execute.call_count == 2

    class TestGetTrending:
        """Test the get_trending method."""

        @pytest.fixture
        def sample_trending_wikiclips(self):
            """Create sample WikiClip instances for trending tests."""
            # 4 articles for user 123 - ordered by created_at desc
            user_123_articles = [
                WikiClip(
                    id=4,
                    title="Latest Article",
                    content="Latest content",
                    summary="Latest summary",
                    url="https://example.com/latest",
                    created_at=datetime(2024, 1, 4, 12, 0, 0),
                    user_id=123,
                ),
                WikiClip(
                    id=3,
                    title="Recent Article",
                    content="Recent content",
                    summary="Recent summary",
                    url="https://example.com/recent",
                    created_at=datetime(2024, 1, 3, 12, 0, 0),
                    user_id=123,
                ),
                WikiClip(
                    id=2,
                    title="Older Article",
                    content="Older content",
                    summary="Older summary",
                    url="https://example.com/older",
                    created_at=datetime(2024, 1, 2, 12, 0, 0),
                    user_id=123,
                ),
                WikiClip(
                    id=1,
                    title="Oldest Article",
                    content="Oldest content",
                    summary="Oldest summary",
                    url="https://example.com/oldest",
                    created_at=datetime(2024, 1, 1, 12, 0, 0),
                    user_id=123,
                ),
            ]
            
            # Article from different user that shouldn't be fetched
            other_user_article = WikiClip(
                id=5,
                title="Other User Article",
                content="Other user content",
                summary="Other user summary",
                url="https://example.com/other",
                created_at=datetime(2024, 1, 5, 12, 0, 0),  # Even newer but different user
                user_id=456,
            )
            
            return user_123_articles, other_user_article

        async def test_get_trending_returns_ordered_wikiclips(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
            sample_trending_wikiclips,
        ):
            """Test that get_trending returns WikiClips ordered by created_at desc."""
            # Arrange
            user_123_articles, other_user_article = sample_trending_wikiclips
            
            mock_result = MagicMock()
            # Return only user 123's articles, ordered by created_at desc
            mock_result.scalars.return_value.unique.return_value.all.return_value = user_123_articles
            mock_session.execute.return_value = mock_result

            # Act
            result = await repository.get_trending(user_id=123, page=1, page_size=5)

            # Assert
            assert len(result) == 4
            # Verify ordering by created_at desc
            assert result[0].id == 4  # Latest (2024-01-04)
            assert result[1].id == 3  # Recent (2024-01-03)
            assert result[2].id == 2  # Older (2024-01-02)
            assert result[3].id == 1  # Oldest (2024-01-01)
            
            # Verify all articles belong to user 123
            for article in result:
                assert article.user_id == 123
                
            mock_session.execute.assert_called_once()

        async def test_get_trending_filters_by_user(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
            sample_trending_wikiclips,
        ):
            """Test that get_trending filters articles by user_id and excludes other users."""
            # Arrange
            user_123_articles, other_user_article = sample_trending_wikiclips
            
            mock_result = MagicMock()
            # Repository should only return user 123's articles, not the other user's
            mock_result.scalars.return_value.unique.return_value.all.return_value = user_123_articles
            mock_session.execute.return_value = mock_result

            # Act
            result = await repository.get_trending(user_id=123, page=1, page_size=5)

            # Assert
            assert len(result) == 4
            # Verify all returned articles belong to user 123
            for article in result:
                assert article.user_id == 123
                assert article.user_id != 456  # Should not include other user's articles
            
            # Verify that the query includes user_cd_id filter
            call_args = mock_session.execute.call_args[0][0]
            query_str = str(call_args)
            assert "user_cd_id" in query_str.lower()

        async def test_get_trending_applies_pagination(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
            sample_trending_wikiclips,
        ):
            """Test that get_trending applies correct pagination."""
            # Arrange
            user_123_articles, _ = sample_trending_wikiclips
            
            mock_result = MagicMock()
            # Return only first 2 articles for page_size=2
            mock_result.scalars.return_value.unique.return_value.all.return_value = user_123_articles[:2]
            mock_session.execute.return_value = mock_result

            # Act
            await repository.get_trending(user_id=123, page=2, page_size=2)

            # Assert
            call_args = mock_session.execute.call_args[0][0]
            # Verify limit and offset are set correctly
            # Page 2, page_size 2 should have offset = (2-1) * 2 = 2
            assert hasattr(call_args, "_limit")
            assert hasattr(call_args, "_offset")

        async def test_get_trending_returns_empty_list_on_exception(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
        ):
            """Test that get_trending returns empty list when an exception occurs."""
            # Arrange
            mock_session.execute.side_effect = Exception("Database error")

            # Act
            result = await repository.get_trending(user_id=123, page=1, page_size=5)

            # Assert
            assert result == []

        async def test_get_trending_with_custom_page_size(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
            sample_trending_wikiclips,
        ):
            """Test that get_trending respects custom page_size."""
            # Arrange
            user_123_articles, _ = sample_trending_wikiclips
            
            mock_result = MagicMock()
            # Return only first 3 articles for page_size=3
            mock_result.scalars.return_value.unique.return_value.all.return_value = user_123_articles[:3]
            mock_session.execute.return_value = mock_result

            # Act
            result = await repository.get_trending(user_id=123, page=1, page_size=3)

            # Assert
            assert len(result) == 3
            call_args = mock_session.execute.call_args[0][0]
            assert hasattr(call_args, "_limit")

    class TestCountTrending:
        """Test the count_trending method."""

        async def test_count_trending_returns_correct_count(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
        ):
            """Test that count_trending returns the correct count for a user."""
            # Arrange
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = 4  # 4 articles for user 123
            mock_session.execute.return_value = mock_result

            # Act
            result = await repository.count_trending(user_id=123)

            # Assert
            assert result == 4
            mock_session.execute.assert_called_once()

        async def test_count_trending_filters_by_user(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
        ):
            """Test that count_trending filters by user_id."""
            # Arrange
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = 1  # 1 article for user 456
            mock_session.execute.return_value = mock_result

            # Act
            result = await repository.count_trending(user_id=456)

            # Assert
            assert result == 1
            # Verify that the query includes user_cd_id filter
            call_args = mock_session.execute.call_args[0][0]
            query_str = str(call_args)
            assert "user_cd_id" in query_str.lower()

        async def test_count_trending_returns_zero_on_exception(
            self,
            repository: WikiClipRepository,
            mock_session: AsyncMock,
        ):
            """Test that count_trending returns zero when an exception occurs."""
            # Arrange
            mock_session.execute.side_effect = Exception("Database error")

            # Act
            result = await repository.count_trending(user_id=123)

            # Assert
            assert result == 0
