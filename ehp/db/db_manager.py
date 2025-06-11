from asyncio import Task, TaskGroup, current_task
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Optional

from fastapi import HTTPException
from sqlalchemy.engine import Result
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session
from sqlalchemy.sql.selectable import Select

from .sqlalchemy_async_connector import async_session_factory


class DBManager:
    def __init__(self):
        self.scoped_session_factory = async_scoped_session(
            async_session_factory, scopefunc=_get_current_task_id
        )
        self._active_sessions: Dict[int, AsyncSession] = {}
        self._transaction_stack: Dict[int, list[AsyncSession]] = {}

    def get_session(self) -> AsyncSession:
        """Get a new session or return an existing one from the current scope"""
        session = self.scoped_session_factory()
        self._active_sessions[id(session)] = session
        return session

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for transaction control with nested transaction support.
        If a transaction is already active for the current scope, joins it instead
        of creating a new one.
        """
        # Get the current task ID to identify the current scope
        current_task_id = _get_current_task_id()

        # Check if we already have a session in this scope
        if (
            hasattr(self, "_current_session")
            and self._current_session.get(current_task_id) is not None
        ):
            # Reuse the existing session for this scope
            session = self._current_session.get(current_task_id)
        else:
            # Create a new session for this scope
            session = self.get_session()
            # Store it for reuse
            if not hasattr(self, "_current_session"):
                self._current_session = {}
            self._current_session[current_task_id] = session

        session_id = id(session)

        # Initialize transaction stack for this session if it doesn't exist
        if session_id not in self._transaction_stack:
            self._transaction_stack[session_id] = []

        try:
            if not self._transaction_stack[session_id]:
                # No active transaction, start a new one
                async with session.begin():
                    self._transaction_stack[session_id].append(session)
                    yield session
                    self._transaction_stack[session_id].pop()
            else:
                # Join existing transaction
                self._transaction_stack[session_id].append(session)
                yield session
                self._transaction_stack[session_id].pop()

        except SQLAlchemyError as e:
            if len(self._transaction_stack[session_id]) == 1:
                # Only rollback if this is the outermost transaction
                await session.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        except Exception as e:
            if len(self._transaction_stack[session_id]) == 1:
                await session.rollback()
            raise e
        finally:
            if self._transaction_stack[session_id]:
                # Clean up only if this is the outermost transaction
                await session.close()
                if session_id in self._active_sessions:
                    del self._active_sessions[session_id]
                del self._transaction_stack[session_id]

                # Also clean up the _current_session reference
                if (
                    hasattr(self, "_current_session")
                    and current_task_id in self._current_session
                ):
                    del self._current_session[current_task_id]

    async def execute_queries_in_parallel(
        self, queries: Dict[str, Select]
    ) -> Dict[str, Task[Result]]:
        """Execute multiple queries in parallel using TaskGroup"""
        tasks = {}
        async with TaskGroup() as task_group:
            for query_name, query in queries.items():
                task = task_group.create_task(self.execute_query(query))
                tasks[query_name] = task
        return tasks

    async def execute_query(self, query: Select) -> Result:
        """Execute a single query within a transaction"""
        async with self.transaction() as session:
            return await session.execute(query)

    def get_current_transaction(self, session: AsyncSession) -> Optional[AsyncSession]:
        """
        Get the current active transaction for a session if it exists.

        Args:
            session: The session to check for active transactions

        Returns:
            Optional[AsyncSession]: The active transaction session or None
        """
        session_id = id(session)
        if (
            session_id in self._transaction_stack
            and self._transaction_stack[session_id]
        ):
            return self._transaction_stack[session_id][-1]
        return None

    def is_in_transaction(self, session: AsyncSession) -> bool:
        """
        Check if the given session is currently in a transaction.

        Args:
            session: The session to check

        Returns:
            bool: True if the session is in a transaction, False otherwise
        """
        session_id = id(session)
        return (
            session_id in self._transaction_stack
            and len(self._transaction_stack[session_id]) > 0
        )

    def get_transaction_depth(self, session: AsyncSession) -> int:
        """
        Get the current transaction nesting depth for a session.

        Args:
            session: The session to check

        Returns:
            int: The number of nested transactions
        """
        session_id = id(session)
        return len(self._transaction_stack.get(session_id, []))

    async def cleanup(self):
        """Cleanup method to handle remaining sessions and transactions"""
        for session in self._active_sessions.values():
            try:
                session_id = id(session)
                if session_id in self._transaction_stack:
                    if session.in_transaction():
                        await session.rollback()
                    del self._transaction_stack[session_id]
                await session.close()
            except Exception as e:
                print(f"Error cleaning up session: {e}")


async def get_simple_db_manager() -> AsyncGenerator[DBManager, None]:
    db_manager = DBManager()
    try:
        yield db_manager
    finally:
        await db_manager.cleanup()


async def get_db_manager() -> AsyncGenerator[DBManager, None]:
    db_manager = DBManager()
    try:
        set_db_manager_in_request_config(db_manager)
        yield db_manager
    finally:
        await db_manager.cleanup()


def set_db_manager_in_request_config(db_manager: DBManager) -> None:
    # TODO: Avoid circular import, take a look at this later.
    try:
        from ehp.base.middleware import get_current_request

        request = get_current_request()
        if hasattr(request.state, "request_config"):
            request.state.request_config["db_manager"] = db_manager
        else:
            request.state.request_config = {"db_manager": db_manager}
    except Exception as e:
        print(f"Error setting db manager in request config: {e}")


def _get_current_task_id() -> int:
    return id(current_task())
