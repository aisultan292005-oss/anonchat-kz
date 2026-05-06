import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import main_router
from middlewares import AntiSpamMiddleware, BanCheckMiddleware
from utils.logging_setup import setup_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()
    logger.info("Starting AnonChat Bot...")

    # Init DB
    await init_db()
    logger.info("Database ready")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Middlewares (order matters)
    dp.message.middleware(BanCheckMiddleware())
    dp.message.middleware(AntiSpamMiddleware())

    dp.include_router(main_router)

    logger.info("Bot polling started")
    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "callback_query", "pre_checkout_query"],
        )
    finally:
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
