from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import database.repo as repo
from database.cities import KZ_CITIES
from keyboards import main_menu_kb
try:
    from handlers.welcome import bottom_menu_kb
except ImportError:
    bottom_menu_kb = main_menu_kb, settings_kb, city_kb, interests_kb
from utils.design import msg_profile, DIV

router = Router()


class SettingsStates(StatesGroup):
    waiting_city = State()
    waiting_interests = State()


@router.message(F.text == "⚙️ Настройки")
async def btn_settings(message: Message):
    user = await repo.get_user(message.from_user.id)
    if not user or not user.is_registered:
        await message.answer("Необходимо пройти регистрацию: /start")
        return
    is_prem = await repo.is_premium_active(message.from_user.id)
    city_label = next((c for l, c in KZ_CITIES if c == user.city), user.city or "не указан")
    await message.answer(msg_profile(user, is_prem, city_label), reply_markup=settings_kb())


@router.callback_query(F.data == "settings:city")
async def cb_settings_city(call: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsStates.waiting_city)
    await call.message.edit_text(
        f"<b>Изменить город</b>\n{DIV}\nВыберите новый город:",
        reply_markup=city_kb(prefix="set_city"),
    )


@router.callback_query(F.data == "set_city_back")
async def cb_set_city_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await repo.get_user(call.from_user.id)
    is_prem = await repo.is_premium_active(call.from_user.id)
    city_label = next((c for l, c in KZ_CITIES if c == user.city), user.city or "не указан") if user else "не указан"
    await call.message.edit_text(msg_profile(user, is_prem, city_label), reply_markup=settings_kb())


@router.callback_query(F.data.startswith("set_city:"), SettingsStates.waiting_city)
async def cb_set_city(call: CallbackQuery, state: FSMContext):
    city = call.data.split(":")[1]
    await repo.update_user(call.from_user.id, city=city)
    await state.clear()
    user = await repo.get_user(call.from_user.id)
    is_prem = await repo.is_premium_active(call.from_user.id)
    city_label = next((c for l, c in KZ_CITIES if c == user.city), city) if user else city
    await call.message.edit_text(
        f"✅ Город изменён на <b>{city_label}</b>\n\n" + msg_profile(user, is_prem, city_label),
        reply_markup=settings_kb(),
    )


@router.callback_query(F.data == "settings:interests")
async def cb_settings_interests(call: CallbackQuery, state: FSMContext):
    user = await repo.get_user(call.from_user.id)
    current = user.interests.split(",") if user and user.interests else []
    await state.set_state(SettingsStates.waiting_interests)
    await call.message.edit_text(
        f"<b>Изменить интересы</b>\n{DIV}\nВыберите до 5 интересов:",
        reply_markup=interests_kb(current, prefix="upd_interest"),
    )


@router.callback_query(F.data.startswith("upd_interest:"), SettingsStates.waiting_interests)
async def cb_upd_interest(call: CallbackQuery, state: FSMContext):
    user = await repo.get_user(call.from_user.id)
    current = user.interests.split(",") if user and user.interests else []
    val = call.data.split(":")[1]

    if val == "done":
        await repo.update_user(call.from_user.id, interests=",".join(current))
        await state.clear()
        is_prem = await repo.is_premium_active(call.from_user.id)
        city_label = next((c for l, c in KZ_CITIES if c == user.city), "") if user else ""
        await call.message.edit_text(
            f"✅ Интересы обновлены\n\n" + msg_profile(user, is_prem, city_label),
            reply_markup=settings_kb(),
        )
        return

    if val in current:
        current.remove(val)
    else:
        if len(current) >= 5:
            await call.answer("Максимум 5 интересов", show_alert=True)
            return
        current.append(val)

    await repo.update_user(call.from_user.id, interests=",".join(current))
    await call.message.edit_reply_markup(reply_markup=interests_kb(current, prefix="upd_interest"))


@router.callback_query(F.data == "upd_interest_back")
async def cb_upd_interest_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await repo.get_user(call.from_user.id)
    is_prem = await repo.is_premium_active(call.from_user.id)
    city_label = next((c for l, c in KZ_CITIES if c == user.city), "") if user else ""
    await call.message.edit_text(msg_profile(user, is_prem, city_label), reply_markup=settings_kb())
