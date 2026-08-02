from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.database.models import User
from app.keyboards.inline import language_keyboard
from app.localization.loader import t
from app.utils.menu_filter import MenuButton

router = Router(name="language")


@router.message(Command("language"))
@router.message(MenuButton("menu_language"))
async def cmd_language(message: Message, db_user: User) -> None:
    await message.answer(t("choose_language", db_user.language), reply_markup=language_keyboard())


@router.message(Command("help"))
@router.message(MenuButton("menu_rules"))
async def cmd_help(message: Message, db_user: User) -> None:
    await message.answer(t("help_text", db_user.language))


@router.message(Command("about"))
async def cmd_about(message: Message, db_user: User) -> None:
    await message.answer(t("about_text", db_user.language))
