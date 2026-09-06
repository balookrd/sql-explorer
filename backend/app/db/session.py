from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from backend.app.core.config import settings

Base = declarative_base()

# Настройка асинхронного engine
engine = create_async_engine(
    settings.database.url,
    echo=settings.server.debug,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    # Если используется локальный SQLite, убедимся что директория существует
    if "sqlite" in settings.database.url:
        import os
        from urllib.parse import urlparse
        parsed = urlparse(settings.database.url)
        db_file = parsed.path
        if db_file:
            db_dir = os.path.dirname(db_file.lstrip("/"))
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
