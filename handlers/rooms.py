"""Permanent themed rooms — pinned chat rooms by topic."""
import logging
from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

import database.repo as repo
from utils.design import DIV

logger = logging.getLogger(__name__)
router = Router()

ROOMS = [
    {"id": "общение",     "name": "💬 Общение",      "desc": "Просто поговорить обо всём"},
    {"id": "флирт",       "name": "💕 Флирт",         "desc": "Лёгкий флирт и знакомства"},
    {"id": "дружба",      "name": "🤝 Дружба",        "desc": "Найти новых друзей"},
    {"id": "юмор",        "name": "😂 Юмор",          "desc": "Шутки, мемы, приколы"},
    {"id": "помощь",      "name": "🆘 Помощь",        "desc": "Поддержка и советы"},
    {"id": "игры",        "name": "🎮 Игры",           "desc": "Обсудить игры и геймплей"},
    {"id": "музыка",      "name": "🎵 Музыка",        "desc": "Меломаны и музыканты"},
    {"id": "астана",      "name": "🏛 Астана",         "desc": "Жители и гости столицы"},
    {"id": "алматы",      "name": "🏙 Алматы",        "desc": "Жители южной столицы"},
]

# Room online counters (in-memory)
_room_counts: dict[str, int] = {r["id"]: 0 for r in ROOMS}


def rooms_kb(current: str | None = None) -> object:
    b = InlineKeyboardBuilder()
    for r in ROOMS:
        tick = "✅ " if r["id"] == current else ""
        count = _room_counts.get(r["id"], 0)
        online = f" · {count} онлайн" if count > 0 else ""
        b.button(
            text=f"{tick}{r['name']}{online}",
            callback_data=f"join_room:{r['id']}"
        )
    b.row(InlineKeyboardButton(text="← Назад", callback_data="nav:main"))
    b.adjust(2)
    return b.as_markup()


def update_room_count():
    """Recalculate room online counts from active queue."""
    for r in ROOMS:
        _room_counts[r["id"]] = 0
    for uid, meta in repo._queue.items():
        room = meta.get("room")
        if room and room in _room_counts:
            _room_counts[room] += 1
    for uid, pid in repo._active.items():
        pass  # Could track room per session


@router.message(F.text == "🚪 Комнаты")
async def btn_rooms(message: Message):
    user = await repo.get_user(message.from_user.id)
    if not user or not user.is_registered:
        await message.answer("Необходимо пройти регистрацию: /start")
        return
    update_room_count()
    await message.answer(
        f"<b>Тематические комнаты</b>\n{DIV}\n"
        f"Выберите комнату — найдём собеседника с такими же интересами.\n"
        f"Текущая комната: <b>{user.preferred_room or 'не выбрана'}</b>",
        reply_markup=rooms_kb(user.preferred_room),
    )


@router.callback_query(F.data.startswith("join_room:"))
async def cb_join_room(call: CallbackQuery, bot: Bot):
    room_id = call.data.split(":")[1]
    room = next((r for r in ROOMS if r["id"] == room_id), None)
    if not room:
        return

    await repo.update_user(call.from_user.id, preferred_room=room_id)
    update_room_count()

    await call.message.edit_text(
        f"<b>{room['name']}</b>\n{DIV}\n"
        f"{room['desc']}\n\n"
        f"Комната выбрана! Теперь нажмите <b>🔍 Найти собеседника</b> —\n"
        f"вас свяжут с кем-то из этой комнаты.",
        reply_markup=rooms_kb(room_id),
    )
    logger.info("User %s joined room: %s", call.from_user.id, room_id)
