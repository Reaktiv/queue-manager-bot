"""
Statistika va umumiy yordam handlerlari.
"""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from i18n.translator import t
from keyboards.reply import HELP_BUTTON
from services.api_client import ApiClient

router = Router(name="stats")


@router.message(Command("stats"))
async def handle_stats(message: Message, state: FSMContext, api_client: ApiClient) -> None:
    data = await state.get_data()
    member_id = data.get("active_member_id")
    lang = (message.from_user.language_code or "uz").split("-")[0] if message.from_user else "uz"

    if member_id is None:
        await message.answer(t("no_active_group", lang=lang))
        return

    result = await api_client.get_member_statistics(member_id)
    if not result.get("success"):
        await message.answer(f"❌ {result.get('message', 'Xatolik yuz berdi')}")
        return

    stats = result["data"]
    await message.answer(
        f"{t('stats_header', lang=lang)}\n\n"
        f"✅ Bajarilgan: {stats['completed']} / {stats['total']}\n"
        f"📈 Bajarish foizi: {stats['completion_rate']}%\n"
        f"⚠️ Joriy jarima: {stats['current_penalty']} ball\n"
        f"🔴 Jami o'tkazib yuborilgan: {stats['total_missed']}"
    )


@router.message(Command("help"))
@router.message(F.text == HELP_BUTTON)
async def handle_help(message: Message) -> None:
    await message.answer(
        "🤖 <b>QueueManagerBot buyruqlari</b>\n\n"
        "<b>Umumiy:</b>\n"
        "/start - ro'yxatdan o'tish\n"
        "/mygroups - guruhlarim va faol guruhni tanlash\n"
        "/join - taklif kodi bilan guruhga qo'shilish\n"
        "/creategroup - yangi guruh yaratish\n\n"
        "<b>A'zo uchun:</b>\n"
        "/mytasks - navbatdagi vazifalarim\n"
        "/turns - guruhdagi barcha joriy navbatlar\n"
        "/stats - statistikam\n\n"
        "<b>Admin uchun:</b>\n"
        "/newtask - yangi vazifa yaratish\n"
        "/tasks - vazifalar ro'yxati va boshqaruvi\n"
        "/members - a'zolar ro'yxati\n"
        "<code>/vacation [member_id]</code> - dam olish rejimini yoqish/o'chirish\n"
        "<code>/setadmin [member_id]</code> - a'zoni admin qilish/tushirish\n\n"
        "/cancel - joriy amalni bekor qilish"
    )