import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database.engine import engine
from app.database.models import Base
from app.handlers import journal, language, leaderboard, play, profile, start
from app.handlers.admin import panel as admin_panel
from app.localization.loader import load_locales
from app.middlewares.user import UserMiddleware
from app.utils.logger import setup_logging

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Creates tables if they don't exist yet — safe alongside migrations/001_init.sql
    which is the source of truth for indexes/views/enums in production."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def register_routers(dp: Dispatcher) -> None:
    dp.include_router(start.router)
    dp.include_router(language.router)
    dp.include_router(play.router)
    dp.include_router(journal.router)
    dp.include_router(profile.router)
    dp.include_router(leaderboard.router)
    dp.include_router(admin_panel.router)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Stub for automatic daily clue release + reminder notifications.
    Wire real jobs here once Season 1 content (release_at per clue) is loaded —
    e.g. scheduler.add_job(release_due_clues, "interval", minutes=5, args=[bot])."""
    scheduler = AsyncIOScheduler()
    scheduler.start()
    return scheduler


async def main() -> None:
    setup_logging()
    load_locales()
    await init_db()

    bot = Bot(token=settings.bot_token)
    storage = RedisStorage.from_url(settings.redis_url)
    dp = Dispatcher(storage=storage)

    dp.update.outer_middleware(UserMiddleware())
    register_routers(dp)

    setup_scheduler(bot)

    logger.info("Project Sherlock bot starting (long polling)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
