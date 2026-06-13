import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, db: AsyncSession):
        """funxtion summary and flow in very short  """
        self.db = db

    async def get_by_session_id(self, session_id: str) -> User | None:
        """funxtion summary and flow in very short  """
        """Fetch a user by their session ID."""
        result = await self.db.execute(select(User).where(User.session_id == session_id))
        return result.scalar_one_or_none()

    async def create_user(self, session_id: str) -> User:
        """funxtion summary and flow in very short  """
        """Create a new user with a given session ID."""
        user = User(session_id=session_id, has_ordered=False)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_or_create_user(self, session_id: str) -> User:
        """funxtion summary and flow in very short  """
        """Fetch a user or create one if they don't exist."""
        try:
            user = await self.get_by_session_id(session_id)
            if not user:
                logger.info(f"Creating a new user profile for session {session_id}")
                user = await self.create_user(session_id)
                logger.info(f"Successfully created new user: {session_id}")
            return user
        except Exception as db_error:
            logger.error(f"Database error while fetching/creating user {session_id}: {db_error}", exc_info=True)
            # Return an unsaved dummy user so the rest of the application doesn't crash
            return User(session_id=session_id, has_ordered=False)
