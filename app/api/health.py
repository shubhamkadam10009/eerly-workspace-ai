from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.db.engine import engine


router = APIRouter(tags=["health"])


@router.get("/health/db")
async def database_health() -> dict[str, str]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

    return {"status": "ok"}


@router.get("/health/db/session")
async def database_session_health(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(text("SELECT 1"))
    value = result.scalar_one()

    return {"status": "ok", "database_result": str(value)}