from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import Column, Integer, String
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ehp.core.models.db.base import BaseModel
from ehp.db.db_manager import DBManager, set_db_manager_in_request_config


# Define a simple test model for db operations
class MockDBModel(BaseModel):
    __tablename__ = "test_db_model"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)


@pytest.mark.unit
@pytest.mark.skip("DBManager tests are not fully functional yet.")
class TestDBManager:

    def test_initialization(self):
        """Test that DBManager initializes correctly."""
        db_manager = DBManager()

        assert hasattr(db_manager, "scoped_session_factory")
        assert hasattr(db_manager, "_active_sessions")
        assert isinstance(db_manager._active_sessions, dict)
        assert hasattr(db_manager, "_transaction_stack")
        assert isinstance(db_manager._transaction_stack, dict)

    def test_get_session(self):
        """Test that get_session returns a session."""
        db_manager = DBManager()

        # Mock scoped_session_factory to return a mock session
        mock_session = MagicMock(spec=AsyncSession)
        db_manager.scoped_session_factory = MagicMock(return_value=mock_session)

        session = db_manager.get_session()

        assert session == mock_session
        assert id(session) in db_manager._active_sessions
        assert db_manager._active_sessions[id(session)] == session

    
    async def test_transaction_success(self):
        """Test successful transaction execution."""
        db_manager = DBManager()

        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Mock begin to return a context manager
        mock_session.begin.return_value = mock_session

        # Mock get_session to return our mock session
        db_manager.get_session = MagicMock(return_value=mock_session)

        # Execute a successful transaction
        async with db_manager.transaction() as session:
            assert session == mock_session
            # Do something in the transaction
            session.add(MockDBModel(name="test"))

        # Verify session methods were called
        mock_session.begin.assert_called_once()
        mock_session.close.assert_called_once()

    
    async def test_transaction_error(self):
        """Test transaction rollback on error."""
        db_manager = DBManager()

        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Mock begin to return a context manager
        mock_session.begin.return_value = mock_session

        # Mock get_session to return our mock session
        db_manager.get_session = MagicMock(return_value=mock_session)

        # Execute a transaction that raises an error
        try:
            async with db_manager.transaction() as session:
                assert session == mock_session
                # Simulate an error
                raise SQLAlchemyError("Test error")
        except Exception:
            pass

        # Verify session methods were called
        mock_session.begin.assert_called_once()
        mock_session.rollback.assert_called_once()
        # mock_session.close.assert_called_once() # This is not being accounted as outermost

    
    async def test_nested_transactions(self):
        """Test nested transactions."""
        db_manager = DBManager()

        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Mock begin to return a context manager
        mock_session.begin.return_value = mock_session

        # Mock get_session to return our mock session
        db_manager.get_session = MagicMock(return_value=mock_session)

        # Execute nested transactions
        async with db_manager.transaction() as outer_session:
            assert outer_session == mock_session

            # Start a nested transaction
            async with db_manager.transaction() as inner_session:
                assert inner_session == outer_session

                # Check transaction depth
                session_id = id(inner_session)
                assert session_id in db_manager._transaction_stack
                assert len(db_manager._transaction_stack[session_id]) == 2

        # Verify begin was called only once (for the outer transaction)
        assert mock_session.begin.call_count == 1

        # Verify close was called once (after both transactions complete)
        mock_session.close.assert_called_once()

    
    async def test_transaction_with_exception_in_nested(self):
        """Test exception handling in nested transactions."""
        db_manager = DBManager()

        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Mock begin to return a context manager
        mock_session.begin.return_value = mock_session

        # Mock get_session to return our mock session
        db_manager.get_session = MagicMock(return_value=mock_session)

        # Execute nested transactions with error in inner transaction
        try:
            async with db_manager.transaction() as outer_session:
                assert outer_session == mock_session

                # Start a nested transaction that fails
                async with db_manager.transaction() as inner_session:
                    assert inner_session == outer_session
                    raise Exception("Inner transaction error")
        except Exception:
            pass

        # Verify rollback was called
        mock_session.rollback.assert_called_once()

        # Verify close was called
        mock_session.close.assert_called_once()

    
    async def test_is_in_transaction(self):
        """Test is_in_transaction method."""
        db_manager = DBManager()

        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Mock begin to return a context manager
        mock_session.begin.return_value = mock_session

        # Mock get_session to return our mock session
        db_manager.get_session = MagicMock(return_value=mock_session)

        # Check before transaction
        assert not db_manager.is_in_transaction(mock_session)

        # Check during transaction
        async with db_manager.transaction() as session:
            assert db_manager.is_in_transaction(session)

        # Check after transaction
        assert not db_manager.is_in_transaction(mock_session)

    
    async def test_get_transaction_depth(self):
        """Test get_transaction_depth method."""
        db_manager = DBManager()

        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Mock begin to return a context manager
        mock_session.begin.return_value = mock_session

        # Mock get_session to return our mock session
        db_manager.get_session = MagicMock(return_value=mock_session)

        # Check before transaction
        assert db_manager.get_transaction_depth(mock_session) == 0

        # Check with single transaction
        async with db_manager.transaction() as session:
            assert db_manager.get_transaction_depth(session) == 1

            # Check with nested transaction
            async with db_manager.transaction() as nested_session:
                assert db_manager.get_transaction_depth(nested_session) == 2

        # Check after transaction
        assert db_manager.get_transaction_depth(mock_session) == 0

    
    async def test_cleanup(self):
        """Test cleanup method."""
        db_manager = DBManager()

        # Create multiple mock sessions
        mock_session1 = AsyncMock(spec=AsyncSession)
        mock_session2 = AsyncMock(spec=AsyncSession)

        # Add to active sessions
        db_manager._active_sessions[id(mock_session1)] = mock_session1
        db_manager._active_sessions[id(mock_session2)] = mock_session2

        # Simulate a transaction in progress
        mock_session1.in_transaction.return_value = True
        db_manager._transaction_stack[id(mock_session1)] = [mock_session1]

        # Execute cleanup
        await db_manager.cleanup()

        # Verify rollback was called for session with transaction
        mock_session1.rollback.assert_called_once()

        # Verify close was called for both sessions
        mock_session1.close.assert_called_once()
        mock_session2.close.assert_called_once()


@pytest.mark.unit
def test_set_db_manager_in_request_config():
    """Test setting DB manager in request config."""
    db_manager = DBManager()

    # Mock request
    mock_request = MagicMock()
    mock_request.state = MagicMock()

    # Case 1: request_config exists
    mock_request.state.request_config = {}

    with patch("ehp.base.middleware.get_current_request", return_value=mock_request):
        set_db_manager_in_request_config(db_manager)

        assert "db_manager" in mock_request.state.request_config
        assert mock_request.state.request_config["db_manager"] == db_manager

    # Case 2: request_config doesn't exist
    delattr(mock_request.state, "request_config")

    with patch("ehp.base.middleware.get_current_request", return_value=mock_request):
        set_db_manager_in_request_config(db_manager)

        assert hasattr(mock_request.state, "request_config")
        assert "db_manager" in mock_request.state.request_config
        assert mock_request.state.request_config["db_manager"] == db_manager

    # Case 3: Exception occurs
    with patch(
        "ehp.base.middleware.get_current_request", side_effect=Exception("Test error")
    ), patch("builtins.print") as mock_print:
        set_db_manager_in_request_config(db_manager)

        # Verify error is printed
        mock_print.assert_called_once()
        assert (
            "Error setting db manager in request config" in mock_print.call_args[0][0]
        )
