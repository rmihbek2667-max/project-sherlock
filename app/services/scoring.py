"""Scoring rules live here only — handlers never compute points directly, so
changing the point curve (e.g. for a future harder season) is a one-file edit."""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import POINTS_BY_ATTEMPT
from app.database.models import User


def points_for_attempt(attempt_number: int) -> int:
    return POINTS_BY_ATTEMPT.get(attempt_number, 0)


async def get_leaderboard(session: AsyncSession, season_id: int, limit: int = 10) -> list[dict]:
    """Reads from the season_leaderboard SQL view (see migrations/001_init.sql),
    so ranking logic (highest score, tie broken by earlier completion) lives in
    one place and stays consistent between /leaderboard and /myrank."""
    result = await session.execute(
        text(
            """
            SELECT user_id, full_name, username, total_points, last_completed_at
            FROM season_leaderboard
            WHERE season_id = :season_id
            ORDER BY total_points DESC, last_completed_at ASC
            LIMIT :limit
            """
        ),
        {"season_id": season_id, "limit": limit},
    )
    rows = result.mappings().all()
    return [dict(row) for row in rows]


async def get_user_rank(session: AsyncSession, season_id: int, user_id: int) -> tuple[int, int] | None:
    """Returns (rank, total_points) for a user in a season, or None if they
    have no scored entries yet."""
    result = await session.execute(
        text(
            """
            SELECT rank, total_points FROM (
                SELECT user_id, total_points,
                       ROW_NUMBER() OVER (ORDER BY total_points DESC, last_completed_at ASC) AS rank
                FROM season_leaderboard
                WHERE season_id = :season_id
            ) ranked
            WHERE user_id = :user_id
            """
        ),
        {"season_id": season_id, "user_id": user_id},
    )
    row = result.first()
    return (row.rank, row.total_points) if row else None
