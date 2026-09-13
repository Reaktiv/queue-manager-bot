"""
Guruh a'zolarining vazifa bajarilishini tasdiqlash/rad etish (voting) oqimi.

Bot bir a'zo rasm yuborganda uni guruhga ✅Ha/❌Yo'q tugmalar bilan
joylaydi (bot/handlers/my_tasks.py). Shu yerdagi handlerlar o'sha
tugmalar bosilganda ishlaydi.
"""
import structlog
from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards.inline import completion_vote_keyboard, star_rating_keyboard
from services.api_client import ApiClient

router = Router(name="approvals")
logger = structlog.get_logger()


@router.callback_query(F.data.startswith("vote_yes:") | F.data.startswith("vote_no:"))
async def handle_vote(callback: CallbackQuery, api_client: ApiClient) -> None:
    if callback.data is None or callback.message is None:
        return

    prefix, _, completion_id_str = callback.data.partition(":")
    try:
        completion_id = int(completion_id_str)
    except ValueError:
        await callback.answer()
        return
    approve = prefix == "vote_yes"
    user = callback.from_user

    result = await api_client.vote_completion(user.id, completion_id, approve)
    if not result.get("success"):
        await callback.answer(result.get("message") or "❌ Xatolik yuz berdi", show_alert=True)
        return

    data = result.get("data") or {}
    status = data.get("status")
    yes_count = data.get("yes_count", 0)
    no_count = data.get("no_count", 0)

    if status == "pending":
        try:
            await callback.message.edit_reply_markup(
                reply_markup=completion_vote_keyboard(completion_id, yes_count, no_count)
            )
        except Exception:
            pass
        await callback.answer("✅ Ovozingiz qabul qilindi")
        return

    task_name = data.get("task_name") or "Vazifa"
    assignee_name = data.get("assignee_name") or "A'zo"
    assignee_telegram_id = data.get("assignee_telegram_id")

    if status == "approved":
        result_text = (
            f"✅ <b>Tasdiqlandi!</b> {assignee_name} \"{task_name}\" vazifasini bajardi deb "
            f"topildi. Navbat keyingi a'zoga o'tdi.\n\n"
            f"⭐ Sifat bahosi uchun 1 soat vaqtingiz bor - shu vaqtdan keyin pastdagi tugmalar "
            f"endi baho qabul qilmaydi."
        )
        private_text = f"✅ Sizning \"{task_name}\" vazifangiz guruh tomonidan tasdiqlandi!"
    else:
        result_text = (
            f"❌ <b>Rad etildi.</b> {assignee_name} \"{task_name}\" vazifasini qayta bajarishi "
            f"kerak."
        )
        private_text = (
            f"❌ Sizning \"{task_name}\" vazifangiz guruh tomonidan rad etildi. Iltimos, "
            f"vazifani qayta bajaring va rasm yuboring."
        )

    # Tasdiqlangan bo'lsa - ✅/❌ tugmalari 1-5 yulduz tugmalariga almashadi
    # (guruhdoshlar sifat bahosi berishi uchun), rad etilganda esa tugmalar
    # butunlay olib tashlanadi (bahoga hojat yo'q).
    new_markup = star_rating_keyboard(completion_id) if status == "approved" else None
    try:
        await callback.message.edit_caption(caption=result_text, reply_markup=new_markup)
    except Exception:
        try:
            await callback.message.edit_reply_markup(reply_markup=new_markup)
        except Exception:
            pass

    if assignee_telegram_id:
        try:
            await callback.bot.send_message(assignee_telegram_id, private_text)
        except Exception:
            logger.exception("notify_assignee_failed", assignee_telegram_id=assignee_telegram_id)

    await callback.answer("✅ Ovozingiz qabul qilindi")
