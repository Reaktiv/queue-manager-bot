"""
Bot session middleware: ReplyKeyboardMarkup (doimiy pastki menyu) hech
qachon guruh/superguruh chatiga YETIB BORMASLIGINI kafolatlaydi - bu
yagona, markazlashtirilgan nazorat nuqtasi.

NEGA bu shart, handler ichidagi `message.chat.type == "private"`
tekshiruvi (u ham bor - registration.py, profile.py) kifoya qilmaydi:

1. ReplyKeyboardMarkup foydalanuvchiga emas, CHATga biriktiriladi.
   Handler darajasidagi tekshiruv faqat "bu handler YANGI klaviatura
   yubormasin" degan qoidani ta'minlaydi - lekin bu ikkita bo'shliqni
   yopmaydi:
     a) Agar TUZATISHDAN OLDIN biror guruhga reply keyboard allaqachon
        yuborilgan bo'lsa, u Telegram tomonidan hamon ko'rsatilib
        turadi - "endi yubormaymiz" qoidasi ESKI klaviaturani olib
        tashlamaydi, faqat yangisini oldini oladi.
     b) Kelajakda kimdir yangi handler qo'shib, `chat.type`
        tekshiruvini unutib qo'ysa, xato yana qaytadi - har bir joyda
        alohida tekshiruvga tayanish takrorlanadigan va unutilishi
        mumkin bo'lgan yechim.

2. Bu middleware BARCHA chiqayotgan Bot API so'rovlarini (sendMessage,
   sendPhoto, ...) ko'rib chiqadi va:
     - Agar so'rov ReplyKeyboardMarkup bilan GURUHGA yo'naltirilgan
       bo'lsa - uni ReplyKeyboardRemove()ga almashtiradi (klaviatura
       UMUMAN yuborilmaydi, o'rniga "olib tashlash" buyrug'i ketadi).
     - Agar shu guruhga jarayon davomida BIRINCHI marta xabar
       yuborilayotgan bo'lsa (reply_markup berilmagan holatda) -
       tuzatishdan oldin qolib ketgan klaviaturani bir martalik
       tozalash uchun ReplyKeyboardRemove() qo'shib yuboriladi.

InlineKeyboardMarkup/ForceReply bilan ishlaydigan so'rovlarga (vazifa/
ovoz/reyting tugmalari va h.k.) TEGINILMAYDI - ular xabarning o'ziga
biriktiriladi (chatga emas) va bu muammoga aloqasi yo'q.
"""
from typing import Any

from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove


def _is_group_chat(chat_id: Any) -> bool:
    """
    Telegram ID konvensiyasi: shaxsiy chatlar HAR DOIM musbat ID'ga ega;
    guruh/superguruh/kanal chatlari - manfiy (superguruhlar "-100..."
    bilan boshlanadi). Bu Bot API'ning qat'iy, kafolatlangan qoidasi,
    taxmin emas - shuning uchun chat turini bilish uchun qo'shimcha
    `getChat` so'rovi shart emas.
    """
    return isinstance(chat_id, int) and chat_id < 0


# Jarayon (process) umri davomida har bir guruhga FAQAT BIR MARTA
# "tozalash" (ReplyKeyboardRemove) qo'shiladi - bu tuzatishdan OLDIN
# o'sha guruhda qolib ketgan klaviaturani olib tashlash uchun. Bot
# qayta ishga tushganda ro'yxat tozalanadi - bu shunchaki bir martalik
# ishning takrorlanmasligi uchun, to'g'rilik uchun shart emas (qayta
# yuborilsa ham hech qanday zarari yo'q, faqat ortiqcha).
_cleaned_group_chats: set[int] = set()


async def strip_group_reply_keyboards(make_request: Any, bot: Any, method: Any) -> Any:
    chat_id = getattr(method, "chat_id", None)
    if _is_group_chat(chat_id):
        reply_markup = getattr(method, "reply_markup", None)

        if isinstance(reply_markup, ReplyKeyboardMarkup):
            method.reply_markup = ReplyKeyboardRemove()
            _cleaned_group_chats.add(chat_id)
        elif reply_markup is None and chat_id not in _cleaned_group_chats:
            method.reply_markup = ReplyKeyboardRemove()
            _cleaned_group_chats.add(chat_id)

    return await make_request(bot, method)
