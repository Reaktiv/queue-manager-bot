"""
Guruh a'zolarining bajarilgan (tasdiqlangan) vazifaga sifat bahosi
(1-5 yulduz) qo'yish oqimi.

Bu `approvals.py`dagi tasdiqlash/rad etish ovozidan ALOHIDA: approve/reject
"bajarildimi?" degan savolga javob beradi, rating esa "qanday bajarildi?"
ga. Tasdiqlangan topshiriq uchun bot ✅/❌ tugmalarini ⭐ tugmalariga
almashtiradi (approvals.py'dagi `handle_vote`), shu yerdagi handler o'sha
tugmalar bosilganda ishlaydi. Klaviatura doimiy qoladi - bir nechta
guruhdosh baho bera oladi.
"""
import structlog
from aiogram import F, Router
from aiogram.types import CallbackQuery

from services.api_client import ApiClient

router = Router(name="ratings")
logger = structlog.get_logger()


@router.callback_query(F.data.startswith("rate:"))
async def handle_rate(callback: CallbackQuery, api_client: ApiClient) -> None:
    if callback.data is None or callback.message is None:
        return

    _, _, rest = callback.data.partition(":")
    completion_id_str, _, stars_str = rest.partition(":")
    try:
        completion_id = int(completion_id_str)
        stars = int(stars_str)
    except ValueError:
        await callback.answer()
        return

    user = callback.from_user
    result = await api_client.rate_completion(user.id, completion_id, stars)
    if not result.get("success"):
        await callback.answer(result.get("message") or "❌ Xatolik yuz berdi", show_alert=True)
        return

    data = result.get("data") or {}
    assignee_name = data.get("assignee_name") or "A'zo"
    completion_avg = data.get("completion_average", 0)
    rating_count = data.get("completion_rating_count", 0)

    await callback.answer(
        f"⭐ Bahoyingiz qabul qilindi! {assignee_name} uchun o'rtacha: "
        f"{completion_avg}/5 ({rating_count} baho)",
        show_alert=False,
    )
