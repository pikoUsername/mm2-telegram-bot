from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import declarative_base


# Базовый класс для моделей SQLAlchemy
Base = declarative_base()


async def create_tables(engine: AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
