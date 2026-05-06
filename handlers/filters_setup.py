import logging
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

import database.repo as repo
from database.models import ROOM_LIST
from keyboards import (
    main_menu_kb, filter_menu_kb, age_range_kb,
    room_kb, lang_kb, interests_kb,
)
from utils.design import DIV

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "🔧 Фильтры")
async def btn_filters(message: Message):
    user = await repo.get_user(message.from_user.id)
    if not user or not user.is_registered:
        await message.answer("⚠️ Сначала зарегистрируйся: /start")
        return
    age_label = f"{user.pref_age_min}–{user.pref_age_max}" if user.pref_age_min else "Любой"
    await message.answer(
        f"<b>Фильтры поиска</b>\n{DIV}\n"
        f"🎂 Возраст: <b>{age_label}</b>\n"
        f"🎯 Интересы: <b>{user.interests or 'не выбраны'}</b>\n"
        f"🚪 Комната: <b>{user.preferred_room or 'любая'}</b>\n"
        f"🌐 Язык: <b>{user.language or 'ru'}</b>",
        reply_markup=filter_menu_kb(),
    )


@router.callback_query(F.data == "filter:age")
async def cb_filter_age(call: CallbackQuery):
    await call.message.edit_text(
        f"<b>Фильтр по возрасту</b>\n{DIV}\nВыберите диапазон:",
        reply_markup=age_range_kb(),
    )


@router.callback_query(F.data.startswith("age_range:"))
async def cb_age_range(call: CallbackQuery):
    val = call.data.split(":")[1]
    if val == "any":
        await repo.update_user(call.from_user.id, pref_age_min=None, pref_age_max=None)
        await call.answer("✅ Фильтр возраста сброшен")
    else:
        mn, mx = int(val.split("-")[0]), int(val.split("-")[1])
        await repo.update_user(call.from_user.id, pref_age_min=mn, pref_age_max=mx)
        await call.answer(f"✅ Возраст {mn}–{mx}")
    user = await repo.get_user(call.from_user.id)
    age_label = f"{user.pref_age_min}–{user.pref_age_max}" if user and user.pref_age_min else "Любой"
    await call.message.edit_text(
        f"<b>Фильтры поиска</b>\n{DIV}\n"
        f"🎂 Возраст: <b>{age_label}</b>\n"
        f"🎯 Интересы: <b>{user.interests or 'не выбраны'}</b>\n"
        f"🚪 Комната: <b>{user.preferred_room or 'любая'}</b>\n"
        f"🌐 Язык: <b>{user.language or 'ru'}</b>",
        reply_markup=filter_menu_kb(),
    )


@router.callback_query(F.data == "filter:interests")
async def cb_filter_interests(call: CallbackQuery):
    user = await repo.get_user(call.from_user.id)
    current = user.interests.split(",") if user and user.interests else []
    await call.message.edit_text(
        f"<b>Фильтр по интересам</b>\n{DIV}\nВыберите интересы собеседника:",
        reply_markup=interests_kb(current, prefix="search_interest"),
    )


@router.callback_query(F.data.startswith("search_interest:"))
async def cb_search_interest(call: CallbackQuery):
    user = await repo.get_user(call.from_user.id)
    current = user.interests.split(",") if user and user.interests else []
    val = call.data.split(":")[1]
    if val == "done":
        await repo.update_user(call.from_user.id, interests=",".join(current))
        await call.message.edit_text(
            f"<b>Фильтры поиска</b>\n{DIV}\n"
            f"🎯 Интересы: <b>{','.join(current) or 'не выбраны'}</b>",
            reply_markup=filter_menu_kb(),
        )
        return
    if val in current:
        current.remove(val)
    else:
        current.append(val)
    await repo.update_user(call.from_user.id, interests=",".join(current))
    await call.message.edit_reply_markup(reply_markup=interests_kb(current, prefix="search_interest"))


@router.callback_query(F.data == "search_interest_back")
async def cb_search_interest_back(call: CallbackQuery):
    user = await repo.get_user(call.from_user.id)
    age_label = f"{user.pref_age_min}–{user.pref_age_max}" if user and user.pref_age_min else "Любой"
    await call.message.edit_text(
        f"<b>Фильтры поиска</b>\n{DIV}\n"
        f"🎂 Возраст: <b>{age_label}</b>\n"
        f"🎯 Интересы: <b>{user.interests if user else 'не выбраны'}</b>\n"
        f"🚪 Комната: <b>{user.preferred_room if user else 'любая'}</b>",
        reply_markup=filter_menu_kb(),
    )


@router.callback_query(F.data == "filter:room")
async def cb_filter_room(call: CallbackQuery):
    user = await repo.get_user(call.from_user.id)
    await call.message.edit_text(
        f"<b>VIP-комнаты</b>\n{DIV}\nВыберите тему общения:",
        reply_markup=room_kb(user.preferred_room if user else None),
    )


@router.callback_query(F.data.startswith("room:"))
async def cb_room(call: CallbackQuery):
    val = call.data.split(":")[1]
    room = None if val == "any" else val
    await repo.update_user(call.from_user.id, preferred_room=room)
    await call.answer(f"✅ Комната: {room or 'любая'}")
    user = await repo.get_user(call.from_user.id)
    await call.message.edit_reply_markup(reply_markup=room_kb(user.preferred_room if user else None))


@router.callback_query(F.data == "filter:lang")
async def cb_filter_lang(call: CallbackQuery):
    user = await repo.get_user(call.from_user.id)
    await call.message.edit_text(
        f"<b>Язык общения</b>\n{DIV}\nСообщения будут переводиться автоматически:",
        reply_markup=lang_kb(user.language if user else "ru"),
    )


@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(call: CallbackQuery):
    code = call.data.split(":")[1]
    await repo.update_user(call.from_user.id, language=code)
    await call.answer("✅ Язык изменён")
    await call.message.edit_reply_markup(reply_markup=lang_kb(code))


@router.callback_query(F.data == "filter:reset")
async def cb_reset_filters(call: CallbackQuery):
    await repo.update_user(
        call.from_user.id,
        pref_age_min=None, pref_age_max=None,
        interests=None, preferred_room=None, pref_gender=None,
    )
    await call.answer("✅ Все фильтры сброшены!", show_alert=True)
    await call.message.edit_text(
        f"<b>Фильтры поиска</b>\n{DIV}\nВсе фильтры сброшены.",
        reply_markup=filter_menu_kb(),
    )
