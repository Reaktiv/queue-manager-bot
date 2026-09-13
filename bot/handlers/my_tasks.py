"""
Oddiy a'zo uchun: o'z vazifalarini ko'rish va rasm bilan bajarish.
"""
from datetime import datetime

import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from handlers.groups import get_active_group_id
from i18n.translator import t
from keyboards.inline import (
    ask_photo_keyboard,
    early_completion_confirm_keyboard,
    future_task_action_keyboard,
    star_rating_keyboard,
    task_action_keyboard,
    turns_view_keyboard,
)
from keyboards.reply import MY_TASKS_BUTTON
from services.api_client import ApiClient
from states.fsm import CompletionStates

router = Router(name="my_tasks")
logger = structlog.get_logger()


def _lang(user) -> str:
    return (user.language_code or "uz").split("-")[0] if user else "uz"


async def _safe_edit(message: Message, text: str, keyboard: InlineKeyboardMarkup) -> None:
    """Xabarni tahrirlaydi; agar Telegram rad etsa (masalan, matn o'zgarmagan
    yoki xabar juda eski bo'lsa) yangi xabar yuboradi - foydalanuvchi
    "kutilmagan xatolik" ko'rmasligi uchun."""
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except Exception:
        try:
            await message.answer(text, reply_markup=keyboard)
        except Exception:
            logger.exception("mytasks_message_edit_failed")


def _format_task_date(date_str: str | None) -> str:
    if not date_str:
        return "Sana yo'q"

    iso_date = date_str.split("T", 1)[0]
    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%d")
    except ValueError:
        return iso_date

    return f"{dt.day}-{dt.strftime('%B').lower()}"


def _future_task_text(task: dict) -> str:
    days = task.get("days_left", 0)
    if days == 1:
        return f"📋 <b>{task['name']}</b> vazifasidagi navbatingizga 1 kun qoldi (Ertaga)."
    if days % 7 == 0 and days > 0:
        weeks = days // 7
        return f"📋 <b>{task['name']}</b> vazifasidagi navbatingizga {weeks} hafta bor."
    return f"📋 <b>{task['name']}</b> vazifasidagi navbatingizga hali {days} kun bor."


def _render_task_view(task: dict, lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """Vazifaning boshlang'ich ko'rinishini (matn + tugmalar) qayta tiklaydi -
    "orqaga" bosilganda yoki tasdiqlash rad etilganda shu holatga qaytiladi."""
    if task.get("is_active_now", True):
        return t("task_assigned_to_you", lang=lang, task=task["name"]), task_action_keyboard(task["id"])
    return _future_task_text(task), future_task_action_keyboard(task["id"])


@router.message(Command("mytasks"))
@router.message(F.text == MY_TASKS_BUTTON)
async def handle_my_tasks(message: Message, state: FSMContext, api_client: ApiClient) -> None:
    group_id = await get_active_group_id(state)
    lang = _lang(message.from_user)
    if group_id is None:
        await message.answer(t("no_active_group", lang=lang))
        return

    user = message.from_user
    result = await api_client.get_my_tasks(user.id, group_id)
    tasks = result.get("data") or []

    if not tasks:
        await message.answer(
            t("no_tasks", lang=lang) or "Sizda joriy vazifalar yo'q.",
            reply_markup=turns_view_keyboard()
        )
        return

    # Har bir vazifa haqidagi ma'lumot FSM'ga keshlanadi - "orqaga"/tasdiqlash
    # bosqichlarida qayta backend'ga murojaat qilmasdan shu yerdan matn va
    # holatni (muddati kelganmi yoki oldinroqmi) tiklash uchun.
    mt_tasks = {str(task["id"]): task for task in tasks}
    await state.update_data(mt_tasks=mt_tasks)

    for task in tasks:
        text, keyboard = _render_task_view(task, lang)
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("complete:"))
async def handle_complete_start(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.message is None:
        return
    task_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    task = (data.get("mt_tasks") or {}).get(str(task_id))

    if task is not None and not task.get("is_active_now", True):
        # Muddat hali kelmagan - avval tasdiqlash so'raladi.
        await _safe_edit(
            callback.message,
            f"⏳ {_future_task_text(task)}\n\nBaribir hozir bajarishni xohlaysizmi?",
            early_completion_confirm_keyboard(task_id),
        )
        await callback.answer()
        return

    await _start_photo_prompt(callback, state, task_id)


@router.callback_query(F.data.startswith("confirm_early:"))
async def handle_confirm_early(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.message is None:
        return
    _, task_id_str, answer = callback.data.split(":")
    task_id = int(task_id_str)

    if answer == "yes":
        await _start_photo_prompt(callback, state, task_id)
        return

    data = await state.get_data()
    task = (data.get("mt_tasks") or {}).get(str(task_id))
    if task is not None:
        text, keyboard = _render_task_view(task, _lang(callback.from_user))
        await _safe_edit(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_complete:"))
async def handle_cancel_complete(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.message is None:
        return
    task_id = int(callback.data.split(":")[1])

    fsm_data = await state.get_data()
    preserved = {
        k: v for k, v in fsm_data.items() if k.startswith("active_") or k == "mt_tasks"
    }
    await state.clear()
    if preserved:
        await state.set_data(preserved)

    task = (fsm_data.get("mt_tasks") or {}).get(str(task_id))
    if task is not None:
        text, keyboard = _render_task_view(task, _lang(callback.from_user))
        await _safe_edit(callback.message, text, keyboard)
    await callback.answer("Bekor qilindi")


async def _start_photo_prompt(callback: CallbackQuery, state: FSMContext, task_id: int) -> None:
    await state.update_data(completing_task_id=task_id, completing_message_id=callback.message.message_id)
    await state.set_state(CompletionStates.waiting_for_photo)
    await _safe_edit(
        callback.message,
        t("ask_photo", lang=_lang(callback.from_user)),
        ask_photo_keyboard(task_id),
    )
    await callback.answer()


@router.message(CompletionStates.waiting_for_photo, F.photo)
async def handle_photo_received(message: Message, state: FSMContext, api_client: ApiClient, bot) -> None:
    fsm_data = await state.get_data()
    task_id = fsm_data.get("completing_task_id")
    user = message.from_user

    try:
        # Eng katta o'lchamdagi rasmni olamiz
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        photo_bytes_io = await bot.download_file(file.file_path)
        photo_bytes = photo_bytes_io.read()

        caption = message.caption

        result = await api_client.complete_task_with_photo(
            task_id=task_id,
            telegram_id=user.id,
            photo_bytes=photo_bytes,
            photo_filename="photo.jpg",
            caption=caption,
        )

        if result.get("success"):
            # DIQQAT: bu yerda avval o'zgaruvchi nomi `data` edi va yuqoridagi
            # FSM ma'lumotini (`active_group_id` va h.k.) yashirib qo'yardi -
            # pastdagi `finally` bloki keyin ANA SHU (API javobi) obyektidan
            # `active_*` kalitlarni qidirardi, ular u yerda yo'q, natijada
            # foydalanuvchining tanlangan guruhi har muvaffaqiyatli rasm
            # yuborilganda o'chib ketardi. Endi alohida nom ishlatiladi.
            result_data = result.get("data") or {}
            await message.answer(t("task_completed", lang=_lang(user)))

            # Vazifa allaqachon tasdiqlangan - guruh a'zolaridan tasdiq
            # SO'RALMAYDI. Agar guruhda baholay oladigan boshqa a'zo bo'lsa,
            # backend shu ma'lumotlarni qaytaradi va rasm guruhga DARHOL
            # 1-5 yulduz baholash tugmalari bilan yuboriladi - bular faqat
            # sifat bahosi uchun, vazifaning bajarilishiga ta'sir qilmaydi.
            chat_id = result_data.get("telegram_chat_id")
            completion_id = result_data.get("completion_id")
            if chat_id and completion_id:
                task_name = result_data.get("task_name") or "Vazifa"
                member_name = result_data.get("member_name") or user.full_name
                info_caption = (
                    f"✅ <b>{member_name}</b> \"{task_name}\" vazifasini bajardi!\n\n"
                    f"⭐ Sifat bahosi uchun 1 soat vaqtingiz bor - shu vaqtdan keyin pastdagi "
                    f"tugmalar endi baho qabul qilmaydi."
                )
                if caption:
                    info_caption += f"\n\n📝 {caption}"
                try:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=photo.file_id,
                        caption=info_caption,
                        reply_markup=star_rating_keyboard(completion_id),
                    )
                except Exception:
                    logger.exception(
                        "send_completion_photo_failed",
                        chat_id=chat_id,
                        completion_id=completion_id,
                    )
        else:
            await message.answer(f"❌ Xatolik: {result.get('message')}")
    except Exception:
        await message.answer(
            "❌ Rasmni yuklashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        )
    finally:
        # Rasm qabul qilingandan keyin "🔙 Orqaga" tugmasi endi ma'nosiz -
        # bosqich yakunlandi, shuning uchun eski so'rov xabaridan olib
        # tashlanadi (kichik suhbat o'zini tozalaydi).
        prompt_message_id = fsm_data.get("completing_message_id")
        if prompt_message_id:
            try:
                await bot.edit_message_reply_markup(
                    chat_id=message.chat.id, message_id=prompt_message_id, reply_markup=None
                )
            except Exception:
                pass

        # Xatolik bo'lsa ham foydalanuvchi doim "waiting_for_photo" holatidan
        # chiqishi kerak - aks holda /cancel qilmaguncha botga hech narsa yubora
        # olmaydi. `set_data()` ning o'zi FSM HOLATINI o'zgartirmaydi - faqat
        # ma'lumotni almashtiradi - shuning uchun avval `clear()` chaqiriladi,
        # xuddi admin_tasks.py/registration.py/common.py dagi kabi.
        preserved = {
            k: v for k, v in fsm_data.items() if k.startswith("active_") or k == "mt_tasks"
        }
        await state.clear()
        if preserved:
            await state.set_data(preserved)


@router.message(CompletionStates.waiting_for_photo, F.text)
async def handle_photo_missing(message: Message) -> None:
    await message.answer("📷 Iltimos, matn emas, rasm yuboring (yoki /cancel bilan bekor qiling).")


@router.message(Command("turns", "navbatlar"))
async def handle_turns(message: Message, state: FSMContext, api_client: ApiClient) -> None:
    group_id = await get_active_group_id(state)
    lang = _lang(message.from_user)
    if group_id is None:
        # Ilgari bu yerda `"no_active_group" in t` tekshiruvi bor edi - `t`
        # tarjima FUNKSIYASI (lug'at emas), shuning uchun `in` operatori
        # `TypeError: argument of type 'function' is not iterable` bilan
        # yiqilardi va foydalanuvchi faol guruhsiz /turns bossa "kutilmagan
        # xatolik" ko'rardi. `no_active_group` kaliti tarjimalarda mavjud
        # (translator.py), shuning uchun `t()` ni to'g'ridan-to'g'ri chaqirish
        # kifoya - xuddi shu faylning `handle_my_tasks`idagi kabi.
        await message.answer(t("no_active_group", lang=lang))
        return

    result = await api_client.list_group_tasks(group_id)
    tasks = result.get("data") or []
    active_tasks = [t for t in tasks if t.get("is_active", True)]

    if not active_tasks:
        await message.answer("Guruhda faol vazifalar mavjud emas.")
        return

    lines = ["👥 <b>Guruhdagi joriy navbatlar:</b>\n"]
    for task in active_tasks:
        assignee = task.get("current_assignee") or "Hech kim"
        task_date = _format_task_date(task.get("current_turn_date"))
        lines.append(f"📋 <b>{task['name']}</b>: {task_date} - 👤 {assignee}")

    await message.answer("\n".join(lines))


@router.callback_query(F.data == "view_turns")
async def handle_view_turns_callback(callback: CallbackQuery, state: FSMContext, api_client: ApiClient) -> None:
    group_id = await get_active_group_id(state)
    lang = _lang(callback.from_user)

    if group_id is None:
        await callback.message.answer("⚠️ Avval faol guruhni tanlang: /mygroups")
        await callback.answer()
        return

    result = await api_client.list_group_tasks(group_id)
    tasks = result.get("data") or []
    active_tasks = [t for t in tasks if t.get("is_active", True)]

    if not active_tasks:
        await callback.message.answer("Guruhda faol vazifalar mavjud emas.")
        await callback.answer()
        return

    lines = ["👥 <b>Guruhdagi joriy navbatlar:</b>\n"]
    for task in active_tasks:
        assignee = task.get("current_assignee") or "Hech kim"
        task_date = _format_task_date(task.get("current_turn_date"))
        lines.append(f"📋 <b>{task['name']}</b>: {task_date} - 👤 {assignee}")

    await callback.message.answer("\n".join(lines))
    await callback.answer()
