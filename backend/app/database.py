"""Async database setup with SQLAlchemy."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL, echo=False, pool_size=20, max_overflow=10
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default admin user if no users exist
    from sqlalchemy import select, func
    from app.models.models import User
    from app.core.auth import hash_password

    async with async_session() as session:
        result = await session.execute(select(func.count(User.id)))
        count = result.scalar()
        if count == 0:
            user = User(
                username="admin",
                email="admin@taskmesh.dev",
                hashed_password=hash_password("admin"),
                is_admin=True,
            )
            session.add(user)
            await session.commit()
            import structlog
            structlog.get_logger().info("default_user_created", username="admin", password="admin")
