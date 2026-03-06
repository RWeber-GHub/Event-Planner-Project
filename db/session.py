from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.config import settings

ASYNC_DATABASE_URL = settings.DATABASE_URL
print("DATABASE_URL =", ASYNC_DATABASE_URL)
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)