"""Environment-driven configuration. Nothing here should ever be hardcoded
in handlers — add new settings here so ops can change behavior without a
code deploy."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    admin_ids: str = ""
    default_language: str = "en"
    log_level: str = "INFO"

    # Channel subscription gate — leave channel_ids empty to disable the feature entirely.
    # channel_ids: comma-separated list of @usernames (public) and/or -100xxxxxxxxxx IDs (private).
    # channel_invite_urls: comma-separated invite links, SAME ORDER as channel_ids.
    # The bot MUST be an admin of every channel listed, or membership checks will fail.
    channel_ids: str = ""
    channel_invite_urls: str = ""

    @property
    def channel_id_list(self) -> list[str]:
        return [c.strip() for c in self.channel_ids.split(",") if c.strip()]

    @property
    def channel_invite_url_list(self) -> list[str]:
        return [u.strip() for u in self.channel_invite_urls.split(",") if u.strip()]

    @property
    def admin_id_set(self) -> set[int]:
        return {int(x) for x in self.admin_ids.split(",") if x.strip()}


SUPPORTED_LANGUAGES = ("uz", "en", "ru")
LANGUAGE_LABELS = {"uz": "🇺🇿 O'zbekcha", "en": "🇬🇧 English", "ru": "🇷🇺 Русский"}

MAX_ATTEMPTS_PER_CLUE = 3
POINTS_BY_ATTEMPT = {1: 100, 2: 75, 3: 50}  # points if solved on this attempt number
DAY_MAX_POINTS = 100
SEASON_LENGTH_DAYS = 5
SEASON_MAX_POINTS = DAY_MAX_POINTS * SEASON_LENGTH_DAYS

settings = Settings()
