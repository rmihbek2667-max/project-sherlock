from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.config import MAX_ATTEMPTS_PER_CLUE
from app.database.models import Clue, ProgressStatus, Season, User
from app.keyboards.inline import hint_keyboard
from app.localization.loader import t
from app.services import journal_service
from app.services.answer_checker import is_correct
from app.services.scoring import points_for_attempt
from app.utils.menu_filter import AnyMenuButton, MenuButton

router = Router(name="play")


class AnswerFlow(StatesGroup):
    waiting_for_answer = State()


async def _get_active_season(session) -> Season | None:
    result = await session.execute(select(Season).where(Season.is_active.is_(True)))
    return result.scalar_one_or_none()


async def _get_current_clue(session, season: Season) -> Clue | None:
    """The 'current' clue is the earliest released clue in this season that
    isn't already solved/failed by the player — determined per-user in the
    caller, this just fetches all released clues in order."""
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(Clue)
        .where(Clue.season_id == season.id)
        .where(Clue.release_at.is_not(None))
        .where(Clue.release_at <= now)
        .order_by(Clue.day_number)
    )
    return list(result.scalars().all())


@router.message(Command("play"))
@router.message(MenuButton("menu_play"))
async def cmd_play(message: Message, db_user: User, session, state: FSMContext) -> None:
    season = await _get_active_season(session)
    if season is None:
        await message.answer(t("no_active_season", db_user.language))
        return

    released_clues = await _get_current_clue(session, season)
    if not released_clues:
        await message.answer(t("clue_locked", db_user.language))
        return

    # find the first released clue the player hasn't finished yet
    target_clue = None
    for clue in released_clues:
        entry = await journal_service.get_or_create_entry(session, db_user.id, clue.id)
        if entry.status in (ProgressStatus.AVAILABLE,):
            target_clue = (clue, entry)
            break
        if entry.status == ProgressStatus.LOCKED:
            entry.status = ProgressStatus.AVAILABLE
            target_clue = (clue, entry)
            break

    if target_clue is None:
        # everything released so far is already solved/failed
        last_clue = released_clues[-1]
        entry = await journal_service.get_or_create_entry(session, db_user.id, last_clue.id)
        if entry.status == ProgressStatus.SOLVED:
            await message.answer(
                t("clue_already_solved", db_user.language, day=last_clue.day_number, points=entry.points_earned)
            )
        else:
            await message.answer(t("clue_already_failed", db_user.language, day=last_clue.day_number))
        return

    clue, entry = target_clue
    attempts_left = MAX_ATTEMPTS_PER_CLUE - entry.attempts_used
    await message.answer(
        t("clue_header", db_user.language, day=clue.day_number, title=clue.title)
        + "\n\n"
        + t("clue_body", db_user.language, text=clue.clue_text, attempts_left=attempts_left),
        reply_markup=hint_keyboard(db_user.language, clue.id) if clue.hint else None,
    )
    await state.update_data(clue_id=clue.id, journal_entry_id=entry.id)
    await state.set_state(AnswerFlow.waiting_for_answer)
    await message.answer(t("ask_answer", db_user.language, day=clue.day_number))


async def _maybe_send_finale(message: Message, db_user: User, session, solved_clue: Clue) -> None:
    """If the clue just solved is the last day of its season and the season
    has a finale_message configured, send it — this is the 'who did it and
    why' reveal, delivered automatically instead of an admin having to DM it."""
    season = await session.get(Season, solved_clue.season_id)
    if season is None or not season.finale_message:
        return

    result = await session.execute(select(Clue).where(Clue.season_id == season.id).order_by(Clue.day_number.desc()))
    last_clue = result.scalars().first()
    if last_clue is not None and last_clue.id == solved_clue.id:
        await message.answer(season.finale_message)


@router.callback_query(F.data.startswith("hint:"))
async def on_hint_requested(callback: CallbackQuery, db_user: User, session) -> None:
    clue_id = int(callback.data.split(":", 1)[1])
    clue = await session.get(Clue, clue_id)
    if clue is None:
        await callback.answer()
        return
    entry = await journal_service.get_or_create_entry(session, db_user.id, clue.id)
    entry.hint_used = True
    await callback.answer(t("hint_text", db_user.language, hint=clue.hint or t("hint_none", db_user.language)), show_alert=True)


@router.message(StateFilter(AnswerFlow.waiting_for_answer), ~AnyMenuButton())
async def on_answer_submitted(message: Message, db_user: User, session, state: FSMContext) -> None:
    data = await state.get_data()
    clue = await session.get(Clue, data["clue_id"])
    entry = await journal_service.get_or_create_entry(session, db_user.id, clue.id)

    submitted = message.text or ""
    correct = is_correct(submitted, clue.correct_answers)
    attempt_number = entry.attempts_used + 1
    points = points_for_attempt(attempt_number) if correct else 0

    await journal_service.record_attempt(session, entry, submitted, correct, points, used_hint=entry.hint_used)

    if correct:
        await message.answer(t("answer_correct", db_user.language, points=points, attempt=attempt_number))
        await _maybe_send_finale(message, db_user, session, clue)
        await state.clear()
        return

    if entry.attempts_used >= MAX_ATTEMPTS_PER_CLUE:
        await message.answer(t("answer_incorrect_final", db_user.language, day=clue.day_number))
        await state.clear()
        return

    attempts_left = MAX_ATTEMPTS_PER_CLUE - entry.attempts_used
    await message.answer(t("answer_incorrect", db_user.language, attempts_left=attempts_left))
    # stay in AnswerFlow.waiting_for_answer for the next attempt
