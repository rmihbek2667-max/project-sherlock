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
