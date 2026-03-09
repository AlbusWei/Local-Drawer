from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(BASE_DIR, 'local_drawer.db')}"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if engine.url.get_backend_name() == "sqlite":
            result = await conn.execute(text("PRAGMA table_info(image_tasks)"))
            existing_columns = {row[1] for row in result.fetchall()}
            if "params" not in existing_columns:
                await conn.execute(text("ALTER TABLE image_tasks ADD COLUMN params JSON"))
            if "provider_task_id" not in existing_columns:
                await conn.execute(text("ALTER TABLE image_tasks ADD COLUMN provider_task_id VARCHAR"))
            if "image_urls" not in existing_columns:
                await conn.execute(text("ALTER TABLE image_tasks ADD COLUMN image_urls JSON"))
            if "local_paths" not in existing_columns:
                await conn.execute(text("ALTER TABLE image_tasks ADD COLUMN local_paths JSON"))
