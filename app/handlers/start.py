from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from app.config import SUPPORTED_LANGUAGES
from app.database.models import User
from app.keyboards.inline import language_keyboard
from app.keyboards.main_menu import main_menu
from app.localization.loader import t

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User, session) -> None:
    if db_user.language is None:
        await message.answer(t("choose_language", None), reply_markup=language_keyboard())
        return

    await message.answer(
        t("welcome", db_user.language, name=db_user.full_name),
        reply_markup=main_menu(db_user.language),
    )


@router.callback_query(F.data.startswith("lang:"))
async def on_language_chosen(callback: CallbackQuery, db_user: User, session) -> None:
    lang = callback.data.split(":", 1)[1]
    if lang not in SUPPORTED_LANGUAGES:
        return
    db_user.language = lang
    await callback.message.edit_text(t("language_saved", lang))
    await callback.message.answer(
        t("welcome", lang, name=db_user.full_name),
        reply_markup=main_menu(lang),
    )
    await callback.answer()
