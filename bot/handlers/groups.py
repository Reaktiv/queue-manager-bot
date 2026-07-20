"""
Foydalanuvchi bir nechta guruhda a'zo bo'lishi mumkin. Bu handler unga
"faol guruh"ni tanlashga imkon beradi - keyingi barcha buyruqlar
(vazifalar, navbat) shu guruh doirasida ishlaydi.
"""
import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline import group_selection_keyboard
from bot.services.api_client import ApiClient

logger = structlog.get_logger()
router = Router(name="groups")


async def get_active_group_id(state: FSMContext) -> str | int | None:
    data = await state.get_data()
    return data.get("active_group_id")


# 🔴 Ham /mygroups, ham /groups komandasini bir vaqtda ushlaymiz
@router.message(Command("mygroups", "groups"))
async def handle_my_groups(message: Message, api_client: ApiClient) -> None:
    user = message.from_user
    if user is None:
        return

    result = await api_client.list_my_groups(user.id)
    groups = result.get("data") or []

    if not groups:
        await message.answer(
            "ℹ️ Siz hali hech qanday guruhga a'zo emassiz.\n\n"
            "🔑 /join - taklif kodi bilan qo'shilish\n"
            "🏠 /creategroup - yangi guruh yaratish"
        )
        return

    await message.answer(
        "🏠 Sizning guruhlaringiz. Faol guruhni tanlang:",
        reply_markup=group_selection_keyboard(groups),
    )


@router.callback_query(F.data.startswith("select_group:"))
async def handle_select_group(callback: CallbackQuery, state: FSMContext, api_client: ApiClient) -> None:
    if callback.data is None or callback.message is None:
        return

    # 🔴 int() olib tashlandi, chunki group_id UUID (string) bo'lishi mumkin
    group_id = callback.data.split(":")[1]

    user = callback.from_user
    if user is None:
        return

    groups_result = await api_client.list_my_groups(user.id)
    groups = groups_result.get("data") or []

    # 🔴 Ma'lumotlar turidagi farqlar xato bermasligi uchun ikkala tomonni ham str() qilib solishtiramiz
    matched = next((g for g in groups if str(g["id"]) == str(group_id)), None)

    if matched:
        await state.update_data(
            active_group_id=matched["id"],
            active_group_name=matched["name"],
            active_member_role=matched["role"],
            active_member_id=matched["member_id"],
            active_group_timezone=matched.get("timezone", "Asia/Tashkent"),
        )

        group_name = matched["name"]
    else:
        # Agar kutilmaganda ro'yxatdan topilmasa, callback ma'lumotidan foydalanamiz
        await state.update_data(
            active_group_id=group_id,
            active_member_role="member",
            active_member_id=None,
            active_group_timezone="Asia/Tashkent",
        )
        group_name = f"ID: {group_id}"

    await callback.message.edit_text(
        f"🟢 Faol guruh: <b>{group_name}</b> muvaffaqiyatli tanlandi!\n\n"
        "📋 /tasks - vazifalar ro'yxati\n"
        "🙋 /mytasks - mening vazifalarim\n"
        "👥 /members - a'zolar\n"
        "📊 /stats - statistikam"
    )
    await callback.answer()


@router.message(Command("link"))
async def handle_link_group(message: Message, api_client: ApiClient) -> None:
    if message.chat.type not in ["group", "supergroup"]:
        await message.answer("⚠️ Bu buyruqni faqat guruh chatida ishlatish mumkin!")
        return

    user = message.from_user
    if user is None:
        return

    parts = message.text.split() if message.text else []
    if len(parts) < 2:
        await message.answer(
            "⚠️ Guruhni bog'lash uchun taklif kodini kiriting!\n"
            "Format: <code>/link KOD</code> (masalan: <code>/link ECJRCYTX</code>)\n\n"
            "Guruh taklif kodini admin panel yoki shaxsiy chatdagi guruhlar ro'yxatidan olishingiz mumkin."
        )
        return

    invite_code = parts[1].strip().upper()

    result = await api_client.link_group_by_code(
        telegram_id=user.id,
        invite_code=invite_code,
        telegram_chat_id=message.chat.id,
    )

    if result.get("success"):
        group_name = result.get("data", {}).get("group_name", "")
        await message.answer(
            f"✅ <b>{group_name}</b> guruhi ushbu Telegram chatga muvaffaqiyatli bog'landi!\n\n"
            "Endi ushbu guruh uchun barcha navbatlar va eslatmalar shu yerda chiqadi."
        )
    else:
        error_msg = result.get("message") or "Guruhni bog'lab bo'lmadi. Kod noto'g'ri yoki siz guruh admini emassiz."
        await message.answer(f"❌ Xatolik: {error_msg}")
