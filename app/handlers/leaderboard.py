from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from app.database.models import Season, User
from app.localization.loader import t
from app.services.scoring import get_leaderboard
from app.utils.menu_filter import MenuButton

router = Router(name="leaderboard")

MEDALS = ["🥇", "🥈", "🥉"]


@router.message(Command("leaderboard"))
@router.message(MenuButton("menu_leaderboard"))
async def cmd_leaderboard(message: Message, db_user: User, session) -> None:
    result = await session.execute(select(Season).where(Season.is_active.is_(True)))
    season = result.scalar_one_or_none()
    if season is None:
        await message.answer(t("no_active_season", db_user.language))
        return

    rows = await get_leaderboard(session, season.id, limit=10)
    if not rows:
        await message.answer(t("no_active_season", db_user.language))
        return

    lines = [t("leaderboard_header", db_user.language), ""]
    for i, row in enumerate(rows):
        medal = MEDALS[i] if i < 3 else f"{i + 1}."
        name = row["full_name"] or row["username"] or "Detective"
        lines.append(t("leaderboard_row", db_user.language, medal=medal, name=name, score=row["total_points"]))

    await message.answer("\n".join(lines))
