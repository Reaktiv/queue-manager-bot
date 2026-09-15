"""
Service Layer: Bildirishnomalarni tayyorlash va Telegram Bot API orqali
to'g'ridan-to'g'ri yuborish.

Diqqat: Scheduler alohida process bo'lgani uchun (aiogram Dispatcher'siz),
u Telegram Bot API'ga to'g'ridan-to'g'ri HTTP orqali murojaat qiladi.
"""

from html import escape

import httpx
import structlog

from ..core.config import settings
from ..repositories.notification_repository import NotificationTemplateRepository

logger = structlog.get_logger()

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"


def format_telegram_html_mention(full_name: str, telegram_id: int) -> str:
    safe_name = escape(full_name, quote=True)
    return f'<a href="tg://user?id={telegram_id}">{safe_name}</a>'


class NotificationService:
    def __init__(self, template_repository: NotificationTemplateRepository) -> None:
        self._template_repo = template_repository

    def render(self, template: str, **placeholders: str) -> str:
        rendered = template
        for key, value in placeholders.items():
            rendered = rendered.replace(f"{{{key}}}", str(value))
        return rendered

    async def build_message(
        self, group_id: int, template_type: str, language: str = "uz", **placeholders: str
    ) -> str:
        template = await self._template_repo.get_template(group_id, template_type, language)
        return self.render(template, **placeholders)

    async def send_private_message(
        self, telegram_id: int, text: str, reply_markup: dict | None = None
    ) -> bool:
        """
        Foydalanuvchining shaxsiy chatiga xabar yuboradi. `reply_markup`
        berilsa (masalan bir tugmali inline klaviatura), Telegram Bot
        API'ning xom JSON shakli sifatida to'g'ridan-to'g'ri yuboriladi -
        bu yerda aiogram Bot obyekti yo'q (scheduler alohida jarayon),
        shuning uchun oddiy dict yetarli: masalan
        `{"inline_keyboard": [[{"text": "...", "callback_data": "..."}]]}`.
        Botning aiogram qismi bu tugma bosilganda kelgan callback'ni
        odatdagidek qabul qiladi - xabar qaysi yo'l bilan yuborilganidan
        qat'i nazar, callback marshrutlash bot yangilanishlar oqimidan
        ishlaydi.
        """
        if not settings.BOT_TOKEN:
            logger.warning("bot_token_missing", telegram_id=telegram_id)
            return False

        if settings.APP_ENV == "testing" or settings.BOT_TOKEN.startswith("test_"):
            logger.info("mock_telegram_send", telegram_id=telegram_id, text=text)
            return True

        payload: dict = {"chat_id": telegram_id, "text": text, "parse_mode": "HTML"}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        url = f"{TELEGRAM_API_BASE.format(token=settings.BOT_TOKEN)}/sendMessage"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    logger.warning(
                        "telegram_send_failed", status=response.status_code, body=response.text
                    )
                    return False
                return True
            except httpx.HTTPError as exc:
                logger.error("telegram_send_error", error=str(exc))
                return False

    async def send_group_message(
        self, telegram_chat_id: int, text: str, reply_markup: dict | None = None
    ) -> bool:
        """Guruh chatiga xabar yuboradi (agar bot shu guruhga qo'shilgan bo'lsa)."""
        return await self.send_private_message(telegram_chat_id, text, reply_markup=reply_markup)
