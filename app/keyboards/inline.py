from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import LANGUAGE_LABELS, SUPPORTED_LANGUAGES
from app.localization.loader import t


def language_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=LANGUAGE_LABELS[lang], callback_data=f"lang:{lang}")]
        for lang in SUPPORTED_LANGUAGES
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def hint_keyboard(lang: str, clue_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("hint_button", lang), callback_data=f"hint:{clue_id}")]]
    )


def subscribe_keyboard(lang: str, invite_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("subscribe_join_button", lang), url=invite_url)],
            [InlineKeyboardButton(text=t("subscribe_check_button", lang), callback_data="check_subscription")],
        ]
    )
