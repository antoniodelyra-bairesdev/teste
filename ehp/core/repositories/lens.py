from typing import List, TypeVar

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ehp.core.models.db.lens import Lens
from ehp.core.models.db.lens_type import LensType
from ehp.core.models.schema.lens import LensSearchSchema, LensSortStrategy
from ehp.core.repositories.base import BaseRepository
from ehp.utils.base import log_error
from ehp.utils.query_timeout import safe_page_size, with_query_timeout

SelectT = TypeVar("SelectT", bound=Select)


class LensRepository(BaseRepository[Lens]):
    """Repository for Lens operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Lens)

    def apply_filters(
        self,
        query: SelectT,
        search: LensSearchSchema,
        apply_order: bool = True,
    ) -> SelectT:
        """Apply filters to the query based on search parameters."""

        # Search term filter - search in both title and content
        if search.search_term:
            search_filter = or_(
                Lens.title.ilike(f"%{search.search_term}%"),
                Lens.content.ilike(f"%{search.search_term}%"),
            )
            query = query.where(search_filter)

        # Lens type filter - search by name instead of ID
        if search.lens_type_name:
            query = query.join(LensType).where(
                LensType.name.ilike(f"%{search.lens_type_name}%")
            )

        # Disabled filter - by default only show active lenses
        if not search.include_disabled:
            query = query.where(Lens.disabled_at.is_(None))

        # Apply ordering if requested
        if not apply_order:
            return query

        if search.sort_by == LensSortStrategy.CREATION_DATE_ASC:
            query = query.order_by(Lens.created_at.asc())
        elif search.sort_by == LensSortStrategy.CREATION_DATE_DESC:
            query = query.order_by(Lens.created_at.desc())
        elif search.sort_by == LensSortStrategy.TITLE_ASC:
            query = query.order_by(Lens.title.asc())
        elif search.sort_by == LensSortStrategy.TITLE_DESC:
            query = query.order_by(Lens.title.desc())

        return query

    async def search(self, search: LensSearchSchema) -> List[Lens]:
        """Search for Lenses based on search parameters."""
        try:
            # Ensure safe page size
            safe_size = safe_page_size(search.size)

            # Build query with lens_type relationship loaded
            query = select(Lens).options(selectinload(Lens.lens_type))
            query = self.apply_filters(query, search)

            # Apply pagination
            offset = (search.page - 1) * safe_size
            query = query.limit(safe_size).offset(offset)

            result = await with_query_timeout(self.session.execute(query))
            return list(result.scalars().unique().all())

        except Exception as e:
            log_error(f"Error searching Lenses: {e}")
            return []

    async def count(self, search: LensSearchSchema) -> int:
        """Count Lenses based on search parameters."""
        try:
            query = select(func.count(Lens.id))
            query = self.apply_filters(query, search, apply_order=False)

            result = await with_query_timeout(self.session.execute(query))
            return result.scalar_one()

        except Exception as e:
            log_error(f"Error counting Lenses: {e}")
            return 0

    async def get_by_id_with_type(self, lens_id: int) -> Lens | None:
        """Get a Lens by ID with lens_type relationship loaded."""
        try:
            query = (
                select(Lens)
                .options(selectinload(Lens.lens_type))
                .where(Lens.id == lens_id)
            )
            result = await with_query_timeout(self.session.execute(query))
            return result.scalar_one_or_none()

        except Exception as e:
            log_error(f"Error getting Lens by ID {lens_id}: {e}")
            return None

    async def get_active_lens_types(self) -> List[LensType]:
        """Get all lens types that have at least one active lens."""
        try:
            query = (
                select(LensType)
                .join(Lens)
                .where(Lens.disabled_at.is_(None))
                .distinct()
                .order_by(LensType.name)
            )

            result = await with_query_timeout(self.session.execute(query))
            return list(result.scalars().unique().all())

        except Exception as e:
            log_error(f"Error getting active lens types: {e}")
            return []
