import os
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Primary (recommended): DATABASE_URL_ASYNC from env (.env)
# Dev fallback: SQLite async (lets the app boot even if Postgres/.env is missing)
DATABASE_URL_ASYNC = os.environ.get("DATABASE_URL_ASYNC")
if not DATABASE_URL_ASYNC:
    DATABASE_URL_ASYNC = "sqlite+aiosqlite:///./dev.db"
    print("[db] DATABASE_URL_ASYNC is not set; using dev fallback:", DATABASE_URL_ASYNC)

engine = create_async_engine(DATABASE_URL_ASYNC, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

