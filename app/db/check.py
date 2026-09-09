import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

from sqlalchemy import text

from app.db.engine import engine


async def check_database() -> None:
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        print("Database connection:", result.scalar())


if __name__ == "__main__":
    asyncio.run(check_database())