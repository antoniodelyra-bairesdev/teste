import asyncio
from contextlib import asynccontextmanager
from ehp.core.models.db import Profile
from ehp.db import DBManager
from ehp.db.db_manager import get_managed_session
from ehp.core.repositories.base import BaseRepository


async def setup_profiles():
    mgr = DBManager()
    async with asynccontextmanager(get_managed_session)(mgr) as session:
        # Create default profiles if they do not exist
        repository = BaseRepository(session, Profile)
        default_profiles = [
            Profile(name="Admin", code="admin"),
            Profile(name="User", code="user"),
        ]

        for id, profile in enumerate(default_profiles, 1):
            existing_profile = await repository.get_by_id(id)
            if not existing_profile:
                _ = await repository.create(
                    Profile(
                        name=profile.name,
                        code=profile.code,
                    )
                )
                print(f"Created profile: {profile.name} with code: {profile.code}")
            else:
                print(
                    f"Profile already exists: {existing_profile.name} with code: {existing_profile.code}"
                )

        await session.commit()

asyncio.run(setup_profiles())
