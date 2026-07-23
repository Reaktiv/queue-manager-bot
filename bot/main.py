import asyncio
import os

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from bot.handlers import approvals, common, registration, groups, admin_tasks, my_tasks, stats
from bot.services.api_client import ApiClient
from dotenv import load_dotenv

load_dotenv()

logger = structlog.get_logger()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
APP_ENV = os.getenv("APP_ENV", "production")


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable o'rnatilmagan")

    bot_internal_secret = os.getenv("BOT_INTERNAL_SECRET", "")
    insecure_defaults = {"", "my_super_secret_key_123", "CHANGE_ME_IN_PRODUCTION"}
    if APP_ENV == "production" and bot_internal_secret in insecure_defaults:
        raise RuntimeError(
            "BOT_INTERNAL_SECRET production muhitida standart/bo'sh qiymatda qolib "
            "ketgan - .env faylida uni backend bilan bir xil, haqiqiy maxfiy "
            "qiymatga o'rnating."
        )

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    api_client = ApiClient(base_url=BACKEND_URL)
    dp["api_client"] = api_client

    @dp.errors()
    async def handle_unexpected_error(event: ErrorEvent) -> bool:
        """
        Har qanday handler'da ushlanmagan xatolik shu yerga tushadi. Buni
        qo'ymasak, callback_query so'rovlari hech qachon `answer()`
        qilinmaydi va foydalanuvchi tugmasi cheksiz "yuklanmoqda" holatida
        muallaq qolib ketaveradi.
        """
        logger.error(
            "unhandled_bot_error",
            error=str(event.exception),
            update_type=event.update.event_type,
        )
        callback = event.update.callback_query
        if callback is not None:
            try:
                await callback.answer("❌ Kutilmagan xatolik yuz berdi. Qayta urinib ko'ring.", show_alert=False)
            except Exception:
                pass
        elif event.update.message is not None:
            try:
                await event.update.message.answer("❌ Kutilmagan xatolik yuz berdi. Qayta urinib ko'ring.")
            except Exception:
                pass
        return True

    dp.include_router(common.router)
    dp.include_router(registration.router)
    dp.include_router(groups.router)
    dp.include_router(admin_tasks.router)
    dp.include_router(my_tasks.router)
    dp.include_router(approvals.router)
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
