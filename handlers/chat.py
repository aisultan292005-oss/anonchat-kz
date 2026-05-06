import logging
from aiogram import Bot, F, Router
from aiogram.types import Message

import database.repo as repo
from database.models import Gender, User
from database.cities import KZ_CITIES
from keyboards import main_menu_kb
from handlers.welcome import bottom_menu_kb, chat_bottom_kb, queue_bottom_kb
from middlewares import cancel_inactivity_timer, reset_inactivity_timer
from utils.translator import translate
from utils.design import (
    msg_partner_found, msg_searching, msg_partner_left, msg_partner_switched,
    msg_chat_ended, msg_not_in_chat, msg_already_in_chat, msg_search_cancelled,
    msg_continue_last, msg_continue_incoming, msg_inactivity, msg_inactivity_partner,
)

logger = logging.getLogger(__name__)
router = Router()


def _city_label(user: User | None) -> str:
    if not user or not user.city:
        return ""
    return next((c for l, c in KZ_CITIES if c == user.city), user.city)


def _interests_match(a: str | None, b: str | None) -> int:
    if not a or not b:
        return 0
    return len(set(a.split(",")) & set(b.split(",")))


def _age_ok(age, mn, mx) -> bool:
    if not age or (not mn and not mx):
        return True
    return (mn or 0) <= age <= (mx or 99)


async def _find_best_match(user_id: int, user: User) -> int | None:
    is_prem = await repo.is_premium_active(user_id)
    candidates = [(uid, m) for uid, m in repo._queue.items() if uid != user_id]
    if not candidates:
        return None

    scored = []
    for cid, meta in candidates:
        candidate = await repo.get_user(cid)
        if not candidate:
            continue
        score = 0

        if not _age_ok(candidate.age, user.pref_age_min, user.pref_age_max):
            continue
        if not _age_ok(user.age, candidate.pref_age_min, candidate.pref_age_max):
            continue

        if user.preferred_room and candidate.preferred_room:
            if user.preferred_room != candidate.preferred_room:
                continue
        if user.preferred_room:
            score += 3

        if is_prem and user.pref_gender:
            if candidate.gender != user.pref_gender:
                continue

        score += _interests_match(user.interests, candidate.interests) * 2
        if meta.get("premium"):
            score += 1

        # Same city bonus
        if user.city and candidate.city and user.city == candidate.city:
            score += 1

        scored.append((score, cid))

    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][1]


async def _do_search(user_id: int, user: User, bot: Bot) -> None:
    is_prem = await repo.is_premium_active(user_id)
    pref = user.pref_gender if is_prem else None
    partner_id = await _find_best_match(user_id, user)

    # Notify subscribed users
    from handlers.notifications import notify_searchers
    await notify_searchers(user_id, bot)

    if partner_id is not None:
        session_id = await repo.create_session(user_id, partner_id)
        repo.connect(user_id, partner_id, session_id)
        partner = await repo.get_user(partner_id)

        common = _interests_match(user.interests, partner.interests if partner else None)
        p_gender = str(partner.gender).replace("Gender.", "") if partner else "male"
        p_city = _city_label(partner)
        p_age = partner.age or 0 if partner else 0
        p_room = user.preferred_room

        await bot.send_message(user_id,
            msg_partner_found(p_gender, p_age, p_city, common, p_room),
            reply_markup=chat_bottom_kb())

        my_gender = str(user.gender).replace("Gender.", "")
        my_city = _city_label(user)
        my_age = user.age or 0
        await bot.send_message(partner_id,
            msg_partner_found(my_gender, my_age, my_city, common, p_room),
            reply_markup=chat_bottom_kb())

        await repo.update_user(user_id, last_partner_id=partner_id)
        await repo.update_user(partner_id, last_partner_id=user_id)
        reset_inactivity_timer(user_id, bot)
        reset_inactivity_timer(partner_id, bot)
        logger.info("Matched %s <-> %s (session %s)", user_id, partner_id, session_id)
    else:
        repo.enqueue(user_id, pref, is_prem)
        await bot.send_message(user_id, msg_searching(), reply_markup=queue_bottom_kb())


async def _require_registered(message: Message) -> User | None:
    user = await repo.get_user(message.from_user.id)
    if not user or not user.is_registered:
        await message.answer("Сначала необходимо пройти регистрацию: /start")
        return None
    return user


@router.message(F.text == "🔍 Найти собеседника")
async def btn_find(message: Message, bot: Bot):
    user = await _require_registered(message)
    if not user:
        return
    if repo.in_chat(message.from_user.id):
        await message.answer(msg_already_in_chat())
        return
    if repo.in_queue(message.from_user.id):
        await message.answer("Поиск уже запущен. Ожидайте или нажмите <b>Отмена поиска</b>.")
        return
    await _do_search(message.from_user.id, user, bot)


@router.message(F.text == "🔄 Продолжить с последним")
async def btn_continue_last(message: Message, bot: Bot):
    user = await _require_registered(message)
    if not user or not user.last_partner_id:
        await message.answer("Нет данных о предыдущем собеседнике.", reply_markup=bottom_menu_kb())
        return
    partner = await repo.get_user(user.last_partner_id)
    if not partner or not partner.is_registered or partner.is_banned:
        await message.answer("Собеседник недоступен.", reply_markup=bottom_menu_kb())
        return
    if repo.in_chat(user.last_partner_id) or repo.in_queue(user.last_partner_id):
        await message.answer("Собеседник сейчас занят. Попробуйте позже.", reply_markup=bottom_menu_kb())
        return

    session_id = await repo.create_session(message.from_user.id, user.last_partner_id)
    repo.connect(message.from_user.id, user.last_partner_id, session_id)

    p_gender = str(partner.gender).replace("Gender.", "")
    p_city = _city_label(partner)
    p_age = partner.age or 0

    await message.answer(msg_continue_last(p_gender, p_age, p_city), reply_markup=chat_bottom_kb())
    await bot.send_message(user.last_partner_id, msg_continue_incoming(), reply_markup=chat_bottom_kb())
    reset_inactivity_timer(message.from_user.id, bot)
    reset_inactivity_timer(user.last_partner_id, bot)


@router.message(F.text == "❌ Отмена поиска")
async def btn_cancel_search(message: Message):
    if repo.in_queue(message.from_user.id):
        repo.dequeue(message.from_user.id)
        await message.answer(msg_search_cancelled(), reply_markup=bottom_menu_kb())
    else:
        await message.answer("Вы не находитесь в очереди.", reply_markup=bottom_menu_kb())


async def _end_chat(user_id: int, bot: Bot, reason: str = "ended") -> int | None:
    partner_id = repo.get_partner(user_id)
    session_id = repo.get_session_db_id(user_id)
    repo.disconnect(user_id)
    cancel_inactivity_timer(user_id)
    if session_id:
        await repo.close_session(session_id)
    if partner_id:
        cancel_inactivity_timer(partner_id)
        if reason == "next":
            await bot.send_message(partner_id, msg_partner_switched(), reply_markup=queue_bottom_kb())
            partner = await repo.get_user(partner_id)
            if partner:
                await _do_search(partner_id, partner, bot)
        else:
            await bot.send_message(partner_id, msg_partner_left(), reply_markup=bottom_menu_kb())
        # Ask for rating
        from handlers.rating import ask_rating
        await ask_rating(user_id, partner_id, bot)
        await ask_rating(partner_id, user_id, bot)
    return partner_id


@router.message(F.text == "⏭ Следующий")
async def btn_next(message: Message, bot: Bot):
    if not repo.in_chat(message.from_user.id):
        await message.answer(msg_not_in_chat(), reply_markup=bottom_menu_kb())
        return
    await _end_chat(message.from_user.id, bot, reason="next")
    user = await repo.get_user(message.from_user.id)
    await _do_search(message.from_user.id, user, bot)


@router.message(F.text == "🚪 Завершить")
async def btn_stop(message: Message, bot: Bot):
    if repo.in_queue(message.from_user.id):
        repo.dequeue(message.from_user.id)
        await message.answer(msg_search_cancelled(), reply_markup=bottom_menu_kb())
        return
    if not repo.in_chat(message.from_user.id):
        await message.answer(msg_not_in_chat(), reply_markup=bottom_menu_kb())
        return
    await _end_chat(message.from_user.id, bot, reason="ended")
    await message.answer(msg_chat_ended(), reply_markup=bottom_menu_kb())


# ── Relay ─────────────────────────────────────────────────────────────────────

async def _relay(user_id: int, bot: Bot, send_fn, content: str = ""):
    partner_id = repo.get_partner(user_id)
    if not partner_id:
        return False
    try:
        await send_fn(partner_id)
        reset_inactivity_timer(user_id, bot)
        reset_inactivity_timer(partner_id, bot)
        await repo.increment_messages(user_id)
        if content:
            session_id = repo.get_session_db_id(user_id)
            if session_id:
                await repo.save_message(session_id, user_id, content)
        return True
    except Exception as e:
        logger.warning("Relay failed %s->%s: %s", user_id, partner_id, e)
        return False


SYSTEM_BUTTONS = {
    "🔍 Найти собеседника", "⏭ Следующий", "🚪 Завершить",
    "🚨 Пожаловаться", "❌ Отмена поиска", "⭐ Premium",
    "📊 Статистика", "⚙️ Настройки", "🔧 Фильтры", "🔄 Продолжить с последним",
}


@router.message(F.text & ~F.text.startswith("/") & ~F.text.in_(SYSTEM_BUTTONS))
async def relay_text(message: Message, bot: Bot):
    uid = message.from_user.id
    if not repo.in_chat(uid):
        await message.answer(msg_not_in_chat(), reply_markup=bottom_menu_kb())
        return
    partner_id = repo.get_partner(uid)
    text = message.text
    user = await repo.get_user(uid)
    partner = await repo.get_user(partner_id) if partner_id else None
    if user and partner and user.language != partner.language:
        text = await translate(text, user.language, partner.language)
    await repo.touch_user(uid)
    ok = await _relay(uid, bot, lambda pid: bot.send_message(pid, text), content=f"[text] {message.text[:200]}")
    if not ok:
        await message.answer("Сообщение не доставлено.", reply_markup=bottom_menu_kb())


@router.message(F.photo)
async def relay_photo(message: Message, bot: Bot):
    if not repo.in_chat(message.from_user.id): return
    p = message.photo[-1]
    await _relay(message.from_user.id, bot,
        lambda pid: bot.send_photo(pid, p.file_id, caption=message.caption), content="[фото]")


@router.message(F.video)
async def relay_video(message: Message, bot: Bot):
    if not repo.in_chat(message.from_user.id): return
    await _relay(message.from_user.id, bot,
        lambda pid: bot.send_video(pid, message.video.file_id, caption=message.caption), content="[видео]")


@router.message(F.animation)
async def relay_gif(message: Message, bot: Bot):
    if not repo.in_chat(message.from_user.id): return
    await _relay(message.from_user.id, bot,
        lambda pid: bot.send_animation(pid, message.animation.file_id), content="[gif]")


@router.message(F.sticker)
async def relay_sticker(message: Message, bot: Bot):
    if not repo.in_chat(message.from_user.id): return
    await _relay(message.from_user.id, bot,
        lambda pid: bot.send_sticker(pid, message.sticker.file_id))


@router.message(F.voice)
async def relay_voice(message: Message, bot: Bot):
    if not repo.in_chat(message.from_user.id): return
    await _relay(message.from_user.id, bot,
        lambda pid: bot.send_voice(pid, message.voice.file_id), content="[голосовое]")


@router.message(F.video_note)
async def relay_video_note(message: Message, bot: Bot):
    if not repo.in_chat(message.from_user.id): return
    await _relay(message.from_user.id, bot,
        lambda pid: bot.send_video_note(pid, message.video_note.file_id))
