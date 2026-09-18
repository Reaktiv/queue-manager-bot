"""
Guruh a'zolarining bajarilgan vazifani ✅/❌ ovoz berib tasdiqlashi
(yoki rad etishi) oqimi.

Rasm yuklangan zahoti topshiriq PENDING holatida guruhga yuboriladi
(bot/handlers/my_tasks.py, `completion_vote_keyboard`). Bajaruvchidan
tashqari faol a'zolarning yarmidan ko'pi "Ha" desa - navbat keyingi
a'zoga o'tadi; yarmidan ko'pi "Yo'q" desa - vazifa shu a'zoda qoladi,
u qaytadan bajarishi kerak. Ko'pchilik hosil bo'lguncha tugmalar
doimiy qoladi - bir nechta kishi ovoz bera olishi kerak.
"""
import structlog
from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards.inline import completion_vote_keyboard
from services.api_client import ApiClient

router = Router(name="votes")
logger = structlog.get_logger()


@router.callback_query(F.data.startswith("vote:"))
async def handle_vote(callback: CallbackQuery, api_client: ApiClient, bot) -> None:
    if callback.data is None or callback.message is None:
        return

    _, _, rest = callback.data.partition(":")
    completion_id_str, _, choice = rest.partition(":")
    try:
        completion_id = int(completion_id_str)
    except ValueError:
        await callback.answer()
        return
    if choice not in ("yes", "no"):
        await callback.answer()
        return

    user = callback.from_user
    result = await api_client.vote_completion(user.id, completion_id, choice == "yes")
    if not result.get("success"):
        await callback.answer(result.get("message") or "❌ Xatolik yuz berdi", show_alert=True)
        return

    data = result.get("data") or {}
    task_name = data.get("task_name") or "Vazifa"
    assignee_name = data.get("assignee_name") or "A'zo"
    assignee_telegram_id = data.get("assignee_telegram_id")
    yes, no, needed = data.get("yes", 0), data.get("no", 0), data.get("needed", 1)
    resolution = data.get("resolution")

    if resolution is None:
        tally_line = f"✅ {yes}/{needed} · ❌ {no}/{needed}"
        caption = (
            f"🗳 <b>{assignee_name}</b> \"{task_name}\" vazifasini bajardi deb da'vo qilmoqda.\n\n"
            f"Bajarilganmi? {tally_line}"
        )
        try:
            await callback.message.edit_caption(caption, reply_markup=completion_vote_keyboard(completion_id))
        except Exception:
            pass
        await callback.answer("Ovozingiz qabul qilindi")
        return

    if resolution == "approved":
        caption = (
            f"✅ <b>{task_name}</b> tasdiqlandi ({yes} ha / {no} yo'q) - "
            f"{assignee_name} bajardi, navbat keyingi a'zoga o'tdi."
        )
        dm_text = f"✅ \"{task_name}\" vazifangiz guruh tomonidan tasdiqlandi. Navbat keyingi a'zoga o'tdi."
    else:
        caption = (
            f"❌ <b>{task_name}</b> rad etildi ({yes} ha / {no} yo'q) - "
            f"vazifa qaytadan {assignee_name}ga topshirildi."
        )
        dm_text = f"❌ \"{task_name}\" vazifangiz guruh tomonidan rad etildi. Iltimos, qaytadan bajaring."

    try:
        await callback.message.edit_caption(caption, reply_markup=None)
    except Exception:
        pass
    await callback.answer("Ovozingiz qabul qilindi")

    if assignee_telegram_id:
        try:
            await bot.send_message(assignee_telegram_id, dm_text)
        except Exception:
            logger.exception(
                "vote_resolution_dm_failed",
                assignee_telegram_id=assignee_telegram_id,
                completion_id=completion_id,
            )
