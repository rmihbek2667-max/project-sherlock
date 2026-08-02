from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from sqlalchemy import select

from app.config import settings
from app.database.engine import get_session
from app.database.models import User


class UserMiddleware(BaseMiddleware):
    """Loads (or creates) the User row for whoever sent this update and injects
    it into handler data as `db_user`, so every handler gets user + language
    without re-querying."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        async with get_session() as session:
            result = await session.execute(select(User).where(User.telegram_id == tg_user.id))
            user = result.scalar_one_or_none()
            if user is None:
                user = User(
                    telegram_id=tg_user.id,
                    username=tg_user.username,
                    full_name=tg_user.full_name or "Detective",
                    is_admin=tg_user.id in settings.admin_id_set,
                )
                session.add(user)
                await session.flush()
            data["db_user"] = user
            data["session"] = session
            return await handler(event, data)
