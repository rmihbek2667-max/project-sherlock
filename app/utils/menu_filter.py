"""Reply-keyboard buttons send their own label text as a plain message, so
menu-button presses need a dedicated filter that matches that text in ANY
supported language (since a user's keyboard shows the label in whichever
language they picked)."""

from aiogram.filters import BaseFilter
from aiogram.types import Message

from app.localization.loader import all_translations


class MenuButton(BaseFilter):
    def __init__(self, key: str) -> None:
        self.key = key

    async def __call__(self, message: Message) -> bool:
        return message.text in all_translations(self.key)


MENU_KEYS = (
    "menu_play",
    "menu_journal",
    "menu_leaderboard",
    "menu_profile",
    "menu_rules",
    "menu_language",
)


class AnyMenuButton(BaseFilter):
    """Matches a press of ANY main-menu button, regardless of language. Used to
    stop the answer-submission handler from swallowing a button press as a
    wrong guess while a player is mid-attempt on a clue."""

    async def __call__(self, message: Message) -> bool:
        text = message.text
        return any(text in all_translations(key) for key in MENU_KEYS)
