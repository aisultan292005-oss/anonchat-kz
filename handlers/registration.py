import logging
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database.repo as repo
from config import MAX_AGE, MIN_AGE
from database.models import Gender, INTERESTS_LIST
from database.cities import KZ_CITIES
from keyboards import confirm_age_kb, gender_kb, main_menu_kb, interests_kb
from utils.design import msg_welcome_back, msg_welcome_new, msg_reg_step, msg_reg_complete

logger = logging.getLogger(__name__)
router = Router()


class RegStates(StatesGroup):
    waiting_gender = State()
    waiting_age = State()
    confirm_age = State()
    waiting_city = State()
    waiting_interests = State()


def city_kb():
    b = InlineKeyboardBuilder()
    for label, city in KZ_CITIES:
        b.button(text=city, callback_data=f"reg_city:{city}")
    b.adjust(2)
    return b.as_markup()



@router.callback_query(F.data.startswith("reg_gender:"), RegStates.waiting_gender)
async def cb_gender(call: CallbackQuery, state: FSMContext):
    gender_str = call.data.split(":")[1]
    gender = Gender.male if gender_str == "male" else Gender.female
    await state.update_data(gender=gender)
    await state.set_state(RegStates.waiting_age)
    await call.message.edit_text(msg_reg_step(2, 4, "Введите ваш возраст:"))


@router.message(RegStates.waiting_age)
async def process_age(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    if not text.isdigit():
        await message.answer("Введите возраст числом, например: <b>22</b>")
        return
    age = int(text)
    if age < MIN_AGE:
        await message.answer(f"Сервис доступен только для пользователей <b>{MIN_AGE}+</b>.")
        await state.clear()
        return
    if age > MAX_AGE:
        await message.answer(f"Введите корректный возраст (до {MAX_AGE} лет).")
        return
    await state.update_data(age=age)
    await state.set_state(RegStates.confirm_age)
    await message.answer(
        msg_reg_step(2, 4, f"Ваш возраст: <b>{age} лет</b>. Подтвердите:"),
        reply_markup=confirm_age_kb(),
    )


@router.callback_query(F.data == "age_confirm", RegStates.confirm_age)
async def cb_confirm_age(call: CallbackQuery, state: FSMContext):
    await state.set_state(RegStates.waiting_city)
    await call.message.edit_text(
        msg_reg_step(3, 4, "Выберите ваш город:"),
        reply_markup=city_kb(),
    )


@router.callback_query(F.data.startswith("reg_city:"), RegStates.waiting_city)
async def cb_city(call: CallbackQuery, state: FSMContext):
    city = call.data.split(":")[1]
    await state.update_data(city=city)
    await state.set_state(RegStates.waiting_interests)
    await call.message.edit_text(
        msg_reg_step(4, 4, f"Город: <b>{city}</b>\n\nВыберите интересы (до 5):"),
        reply_markup=interests_kb([]),
    )


@router.callback_query(F.data.startswith("interest:"), RegStates.waiting_interests)
async def cb_interest_toggle(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected: list = data.get("interests", [])
    interest = call.data.split(":")[1]

    if interest == "done":
        interests_str = ",".join(selected) if selected else ""
        await repo.register_user(call.from_user.id, data["gender"], data["age"])
        await repo.update_user(call.from_user.id, interests=interests_str, city=data.get("city"))
        await state.clear()
        city = data.get("city", "")
        await call.message.edit_text(msg_reg_complete(city, interests_str))
        await call.message.answer(
            "Нажмите <b>Найти собеседника</b> для начала",
            reply_markup=main_menu_kb(),
        )
        logger.info("User %s registered city=%s", call.from_user.id, city)
        # Process referral
        if data.get("referrer_id"):
            from handlers.referral import process_referral
            from aiogram import Bot
            bot = call.bot
            await process_referral(call.from_user.id, data["referrer_id"], bot)
        return

    if interest in selected:
        selected.remove(interest)
    else:
        if len(selected) >= 5:
            await call.answer("Максимум 5 интересов", show_alert=True)
            return
        selected.append(interest)

    await state.update_data(interests=selected)
    await call.message.edit_reply_markup(reply_markup=interests_kb(selected))


@router.callback_query(F.data == "age_cancel")
async def cb_cancel_age(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Регистрация отменена. Введите /start для повтора.")
