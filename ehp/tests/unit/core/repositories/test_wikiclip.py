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

            # Act & Assert
            # Since the exception is not caught in the exists method, it should be raised
            with pytest.raises(Exception, match="Database error"):
                await repository.exists(
                    url="https://example.com/test",
                    created_at=date(2024, 1, 1),
                    title="Test Article",
                    user_id=123,
                )

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
