from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.localization.loader import t


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("menu_play", lang)), KeyboardButton(text=t("menu_journal", lang))],
            [KeyboardButton(text=t("menu_leaderboard", lang)), KeyboardButton(text=t("menu_profile", lang))],
            [KeyboardButton(text=t("menu_rules", lang)), KeyboardButton(text=t("menu_language", lang))],
        ],
        resize_keyboard=True,
    )
