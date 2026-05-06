import random
import logging
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

import database.repo as repo

logger = logging.getLogger(__name__)
router = Router()


class CaptchaStates(StatesGroup):
    waiting_answer = State()


def _make_captcha() -> tuple[str, int, list[int]]:
    """Returns (question_text, correct_answer, all_options)."""
    a = random.randint(2, 12)
    b = random.randint(2, 12)
    correct = a * b
    wrong = set()
    while len(wrong) < 3:
        w = correct + random.randint(-5, 5)
        if w != correct and w > 0:
            wrong.add(w)
    options = list(wrong) + [correct]
    random.shuffle(options)
    return f"{a} × {b} = ?", correct, options


def captcha_kb(options: list[int]) -> object:
    b = InlineKeyboardBuilder()
    for opt in options:
        b.button(text=str(opt), callback_data=f"captcha:{opt}")
    b.adjust(2)
    return b.as_markup()


async def send_captcha(message: Message, state: FSMContext):
    question, correct, options = _make_captcha()
    await state.set_state(CaptchaStates.waiting_answer)
    await state.update_data(captcha_answer=correct)
    await message.answer(
        f"🤖 <b>Проверка: ты не бот?</b>\n\nРеши пример:\n\n<b>{question}</b>",
        reply_markup=captcha_kb(options),
    )


@router.callback_query(F.data.startswith("captcha:"), CaptchaStates.waiting_answer)
async def cb_captcha(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    correct = data.get("captcha_answer")
    chosen = int(call.data.split(":")[1])

    if chosen == correct:
        await repo.update_user(call.from_user.id, captcha_passed=True)
        await state.clear()
        await call.message.edit_text("✅ Проверка пройдена! Добро пожаловать.")
        logger.info("Captcha passed: %s", call.from_user.id)
        # Continue to registration
        from handlers.registration import start_registration
        await start_registration(call.message, call.from_user.id)
    else:
        # New captcha
        question, correct, options = _make_captcha()
        await state.update_data(captcha_answer=correct)
        await call.message.edit_text(
            f"❌ Неверно! Попробуй ещё раз:\n\n<b>{question}</b>",
            reply_markup=captcha_kb(options),
        )
