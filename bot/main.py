import asyncio
import os

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import registration, groups, admin_tasks, my_tasks, stats
from bot.services.api_client import ApiClient
from dotenv import load_dotenv

load_dotenv()

logger = structlog.get_logger()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable o'rnatilmagan")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    api_client = ApiClient(base_url=BACKEND_URL)
    dp["api_client"] = api_client

    dp.include_router(registration.router)
    dp.include_router(groups.router)
    dp.include_router(admin_tasks.router)
    dp.include_router(my_tasks.router)
    dp.include_router(stats.router)

    logger.info("bot_starting")
    try:
        await dp.start_polling(bot)
    finally:
        if hasattr(api_client, 'close'):
            await api_client.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
