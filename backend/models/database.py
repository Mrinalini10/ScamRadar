from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from models.db_models import Base, AdminConfig
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./scamradar.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed default admin config
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(AdminConfig).where(AdminConfig.id == "global"))
        config = result.scalar_one_or_none()
        if not config:
            session.add(AdminConfig(id="global"))
            await session.commit()
