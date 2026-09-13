"""
Doimiy (pastki) reply klaviaturalar.

Inline tugmalardan farqi: bular aniq bir xabarga bog'lanmagan, chat
ekranining pastida doimo turadi - foydalanuvchi Mini App'ni yoki biror
buyruqni eslab yurmasdan asosiy amallarga bir bosishda o'tishi uchun.
Bir vaqtning o'zida faqat BITTA reply klaviatura faol bo'ladi: yangisi
har doim eskisini almashtiradi.
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

PROFILE_BUTTON = "👤 Profil"
MY_TASKS_BUTTON = "📋 Mening vazifalarim"
HELP_BUTTON = "❓ Yordam"

SHARE_CONTACT_BUTTON = "📱 Raqamni ulashish"
SKIP_CONTACT_BUTTON = "⏭ Hozircha kerak emas"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Asosiy doimiy menyu - /start dan keyin va telefon ulashish/o'tkazib
    yuborish bosqichidan keyin ko'rsatiladi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=PROFILE_BUTTON), KeyboardButton(text=MY_TASKS_BUTTON)],
            [KeyboardButton(text=HELP_BUTTON)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def contact_request_keyboard() -> ReplyKeyboardMarkup:
    """
    Telefon raqamini so'rash uchun. Telegram botlari boshqa birovning
    raqamini so'ray olmaydi - faqat shu "kontakt ulashish" tugmasi
    orqali FOYDALANUVCHINING O'Z raqami olinadi, matn maydoniga yozib
    kiritib bo'lmaydi.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SHARE_CONTACT_BUTTON, request_contact=True)],
            [KeyboardButton(text=SKIP_CONTACT_BUTTON)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
