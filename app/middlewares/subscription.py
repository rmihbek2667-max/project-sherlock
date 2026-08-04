"""Blocks all bot usage until the user has joined the configured channel.
Verified server-side via Telegram's getChatMember API — not a self-reported
checkbox, so it can't be faked. Disabled entirely (fail-open, no gate at all)
if CHANNEL_ID is left blank in config, so this feature is fully optional.

REQUIRES: the bot must be an admin of the target channel, or get_chat_member
will fail. On any lookup error (bot not admin, wrong channel ID, Telegram API
hiccup) we fail OPEN — i.e. let the user through — so a misconfiguration on
your end never locks out every single user; it just means the gate silently
isn't enforced until the config/permissions are fixed."""

import logging
from typing import Any, Awaitable, Callable

from aiogram import Bot
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app.config import settings
from app.database.models import User
from app.keyboards.inline import subscribe_keyboard
from app.localization.loader import t

logger = logging.getLogger(__name__)

CHECK_CALLBACK_DATA = "check_subscription"


class SubscriptionGateMiddleware(BaseMiddleware):
    async def _is_subscribed_to_all(self, bot: Bot, telegram_id: int) -> bool:
        for channel_id in settings.channel_id_list:
            try:
                member = await bot.get_chat_member(chat_id=channel_id, user_id=telegram_id)
                if member.status not in ("member", "administrator", "creator"):
                    return False
            except Exception as exc:  # noqa: BLE001 — deliberately broad: fail-open on ANY lookup issue
                logger.warning("Subscription check failed for %s on %s: %s", telegram_id, channel_id, exc)
                continue  # treat an unreachable/misconfigured channel as not blocking, not as "not subscribed"
        return True

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        if not settings.channel_id_list:
            return await handler(event, data)

        tg_user = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        bot: Bot = data["bot"]
        db_user: User | None = data.get("db_user")
        lang = db_user.language if db_user else None

        subscribed = await self._is_subscribed_to_all(bot, tg_user.id)

        is_check_callback = event.callback_query is not None and event.callback_query.data == CHECK_CALLBACK_DATA
        if is_check_callback:
            if subscribed:
                await event.callback_query.message.edit_text(t("subscription_confirmed", lang))
            else:
                await event.callback_query.answer(t("subscribe_required_alert", lang), show_alert=True)
                return
            await event.callback_query.answer()
            return

        if subscribed:
            return await handler(event, data)

        if event.message:
            await event.message.answer(
                t("subscribe_required", lang), reply_markup=subscribe_keyboard(lang, settings.channel_invite_url_list)
            )
        elif event.callback_query:
            await event.callback_query.answer(t("subscribe_required_alert", lang), show_alert=True)
        return
