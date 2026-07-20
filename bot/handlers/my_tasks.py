"""
Oddiy a'zo uchun: o'z vazifalarini ko'rish va rasm bilan bajarish.
"""
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.handlers.groups import get_active_group_id
from bot.i18n.translator import t
from bot.keyboards.inline import task_action_keyboard
from bot.services.api_client import ApiClient
from bot.states.fsm import CompletionStates

router = Router(name="my_tasks")


def _lang(user) -> str:
    return (user.language_code or "uz").split("-")[0] if user else "uz"


def _format_task_date(date_str: str | None) -> str:
    if not date_str:
        return "Sana yo'q"

    iso_date = date_str.split("T", 1)[0]
    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%d")
    except ValueError:
        return iso_date

    return f"{dt.day}-{dt.strftime('%B').lower()}"


@router.message(Command("mytasks"))
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
        from bot.keyboards.inline import turns_view_keyboard
        await message.answer(
            t("no_tasks", lang=lang) or "Sizda joriy vazifalar yo'q.",
            reply_markup=turns_view_keyboard()
        )
        return

    for task in tasks:
        is_active = task.get("is_active_now", True)
        if is_active:
            await message.answer(
                t("task_assigned_to_you", lang=lang, task=task["name"]),
                reply_markup=task_action_keyboard(task["id"]),
            )
        else:
            days = task.get("days_left", 0)
            if days == 1:
                text = f"📋 <b>{task['name']}</b> vazifasidagi navbatingizga 1 kun qoldi (Ertaga)."
            elif days % 7 == 0:
                weeks = days // 7
                text = f"📋 <b>{task['name']}</b> vazifasidagi navbatingizga {weeks} hafta bor."
            else:
                text = f"📋 <b>{task['name']}</b> vazifasidagi navbatingizga hali {days} kun bor."

            from bot.keyboards.inline import future_task_action_keyboard
            await message.answer(
                text,
                reply_markup=future_task_action_keyboard(task["id"])
            )


@router.callback_query(F.data.startswith("complete:"))
async def handle_complete_start(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.message is None:
        return
    task_id = int(callback.data.split(":")[1])
    await state.update_data(completing_task_id=task_id)
    await state.set_state(CompletionStates.waiting_for_photo)
    await callback.message.answer(t("ask_photo", lang=_lang(callback.from_user)))
    await callback.answer()


@router.message(CompletionStates.waiting_for_photo, F.photo)
async def handle_photo_received(message: Message, state: FSMContext, api_client: ApiClient, bot) -> None:
    data = await state.get_data()
    task_id = data.get("completing_task_id")
    user = message.from_user

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
        await message.answer(t("task_completed", lang=_lang(user)))
    else:
        await message.answer(f"❌ Xatolik: {result.get('message')}")

    await state.set_data({k: v for k, v in data.items() if k.startswith("active_")})


@router.message(CompletionStates.waiting_for_photo, F.text)
async def handle_photo_missing(message: Message) -> None:
    await message.answer("📷 Iltimos, matn emas, rasm yuboring (yoki /cancel bilan bekor qiling).")


@router.message(Command("cancel"))
async def handle_cancel(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_data({k: v for k, v in data.items() if k.startswith("active_")})
    await message.answer("Amal bekor qilindi.")


@router.message(Command("turns", "navbatlar"))
async def handle_turns(message: Message, state: FSMContext, api_client: ApiClient) -> None:
    group_id = await get_active_group_id(state)
    lang = _lang(message.from_user)
    if group_id is None:
        await message.answer(t("no_active_group", lang=lang) if "no_active_group" in t else "⚠️ Avval faol guruhni tanlang: /mygroups")
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
