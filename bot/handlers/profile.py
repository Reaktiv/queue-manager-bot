"""
Doimiy pastki menyudagi "Profil" bo'limi va telefon raqamini
"kontakt ulashish" orqali olish oqimi.
"""
import structlog
from aiogram import F, Router
from aiogram.types import Message

from keyboards.reply import (
    PROFILE_BUTTON,
    SKIP_CONTACT_BUTTON,
    contact_request_keyboard,
    main_menu_keyboard,
)
from services.api_client import ApiClient

router = Router(name="profile")
logger = structlog.get_logger()


@router.message(F.contact)
async def handle_contact_received(message: Message, api_client: ApiClient) -> None:
    contact = message.contact
    user = message.from_user
    if contact is None or user is None:
        return

    # Xavfsizlik: Telegram forward qilingan (boshqa kimningdir) kontakt
    # kartasini ham yuborish imkonini beradi - faqat foydalanuvchining
    # O'Z raqamini qabul qilamiz.
    if contact.user_id is not None and contact.user_id != user.id:
        await message.answer(
            "⚠️ Faqat o'zingizning raqamingizni ulashishingiz mumkin.",
            reply_markup=contact_request_keyboard(),
        )
        return

    result = await api_client.set_phone_number(user.id, contact.phone_number)
    if not result.get("success"):
        await message.answer(
            f"❌ {result.get('message') or 'Raqamni saqlab bo‘lmadi'}",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer("✅ Raqamingiz saqlandi!", reply_markup=main_menu_keyboard())


@router.message(F.text == SKIP_CONTACT_BUTTON)
async def handle_skip_contact(message: Message) -> None:
    await message.answer(
        "Yaxshi, xohlasangiz keyinroq Profil bo'limidan ulashishingiz mumkin.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == PROFILE_BUTTON)
async def handle_profile(message: Message, api_client: ApiClient) -> None:
    user = message.from_user
    if user is None:
        return

    user_result = await api_client.get_user(user.id)
    if not user_result.get("success"):
        await message.answer("❌ Profil topilmadi. Avval /start bosing.")
        return
    user_data = user_result.get("data") or {}

    lines = [
        "👤 <b>Profil</b>",
        "",
        f"Ism: <b>{user_data.get('full_name') or user.full_name}</b>",
        f"Telegram ID: <code>{user_data.get('telegram_id', user.id)}</code>",
    ]

    phone = user_data.get("phone_number")
    lines.append(f"Telefon: <code>{phone}</code>" if phone else "Telefon: ulashilmagan")

    # Reyting a'zo bo'lgan HAR BIR guruh uchun alohida ko'rsatiladi (ular
    # mustaqil - bitta guruhda 5.0, boshqasida 3.5 bo'lishi mumkin). FSM
    # holatidagi "faol guruh"ga tayanmaymiz - u xotirada saqlanadi va bot
    # qayta ishga tushganda yo'qoladi, profil esa har doim to'g'ri
    # ko'rsatilishi kerak.
    groups_result = await api_client.list_my_groups(user.id)
    ratings: list[tuple[str, float]] = []
    for group in groups_result.get("data") or []:
        stats_result = await api_client.get_member_statistics(group["member_id"])
        if stats_result.get("success"):
            rating = (stats_result.get("data") or {}).get("rating_stars")
            if rating is not None:
                ratings.append((group["name"], rating))

    if len(ratings) == 1:
        lines.append(f"Reyting: ⭐ {ratings[0][1]:.2f} / 5")
    elif len(ratings) > 1:
        lines.append("")
        lines.append("Reyting (guruhlar bo'yicha):")
        lines.extend(f"• {name}: ⭐ {rating:.2f} / 5" for name, rating in ratings)

    await message.answer("\n".join(lines))

    if not phone:
        await message.answer(
            "📱 Boshqa a'zolar siz bilan bog'lanishi osonroq bo'lishi uchun "
            "raqamingizni ulashasizmi?",
            reply_markup=contact_request_keyboard(),
        )
