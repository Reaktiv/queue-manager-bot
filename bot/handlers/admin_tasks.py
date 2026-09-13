"""
Admin uchun vazifa yaratish, tahrirlash, navbatni boshqarish handlerlari.
"""
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from handlers.groups import get_active_group_id
from keyboards.inline import (
    admin_task_menu_keyboard,
    confirm_keyboard,
    member_selection_keyboard,
    task_list_keyboard,
    yes_no_keyboard,
)
from services.api_client import ApiClient
from states.fsm import CreateTaskStates, EditReminderStates, ReorderStates
from utils.datetime_utils import get_local_today_in_timezone

router = Router(name="admin_tasks")


def _format_task_date(date_str: str | None) -> str:
    if not date_str:
        return "Sana yo'q"

    iso_date = date_str.split("T", 1)[0]
    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%d")
    except ValueError:
        return iso_date

    return f"{dt.day}-{dt.strftime('%B').lower()}"


async def _require_active_group(message: Message, state: FSMContext) -> int | None:
    group_id = await get_active_group_id(state)
    if group_id is None:
        await message.answer("⚠️ Avval faol guruhni tanlang: /mygroups")
        return None
    return group_id


async def _require_group_admin(state: FSMContext, target: Message | CallbackQuery) -> bool:
    data = await state.get_data()
    if data.get("active_member_role") == "admin":
        return True

    text = "⛔ Sizda bunday huquq yo'q. Bu amal faqat guruh admini uchun."
    if isinstance(target, CallbackQuery):
        if target.message is not None:
            await target.message.answer(text)
        await target.answer("Sizda bunday huquq yo'q", show_alert=True)
        return False

    await target.answer(text)
    return False


@router.message(Command("tasks"))
async def handle_list_tasks(message: Message, state: FSMContext, api_client: ApiClient) -> None:
    group_id = await _require_active_group(message, state)
    if group_id is None:
        return

    result = await api_client.list_group_tasks(group_id)
    tasks = result.get("data") or []
    if not tasks:
        await message.answer("Bu guruhda hali vazifalar yo'q. Yaratish uchun /newtask")
        return

    await message.answer(
        "📋 Guruh vazifalari (boshqarish uchun bosing):",
        reply_markup=task_list_keyboard(tasks, action_prefix="admin_task_menu"),
    )


async def _show_task_menu(
    callback: CallbackQuery, state: FSMContext, api_client: ApiClient, task_id: int
) -> None:
    group_id = await get_active_group_id(state)
    task_title = f"Vazifa #{task_id}"

    if group_id is not None:
        result = await api_client.list_group_tasks(group_id)
        tasks = result.get("data") or []
        task = next((item for item in tasks if item.get("id") == task_id), None)
        if task and task.get("name"):
            task_title = task["name"]

    await callback.message.edit_text(
        f"{task_title} - kerakli amalni tanlang:",
        reply_markup=admin_task_menu_keyboard(task_id),
    )


@router.callback_query(F.data.startswith("admin_task_menu:"))
async def handle_task_menu(callback: CallbackQuery, state: FSMContext, api_client: ApiClient) -> None:
    if callback.data is None or callback.message is None:
        return
    if not await _require_group_admin(state, callback):
        return

    task_id = int(callback.data.split(":")[1])
    await _show_task_menu(callback, state, api_client, task_id)
    await callback.answer()


@router.callback_query(F.data.startswith("preview:"))
async def handle_preview_queue(callback: CallbackQuery, api_client: ApiClient) -> None:
    if callback.data is None or callback.message is None:
        return
    task_id = int(callback.data.split(":")[1])
    result = await api_client.get_queue_preview(task_id)
    entries = result.get("data") or []

    if not entries:
        text = "Navbat bo'sh."
    else:
        lines = ["👀 <b>Navbat:</b>"]
        for index, entry in enumerate(entries, start=1):
            lock_icon = "🔒" if entry["is_locked"] else ""
            name = entry.get("full_name") or f"a'zo #{entry['member_id']}"
            task_date = _format_task_date(entry.get("scheduled_date"))
            lines.append(f"{index}. {task_date}: {name} {lock_icon}".rstrip())
        text = "\n".join(lines)

    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_skip:"))
async def handle_admin_skip(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.message is None:
        return
    if not await _require_group_admin(state, callback):
        return
    task_id = int(callback.data.split(":")[1])

    await callback.message.edit_text(
        "⏭ Joriy a'zoni o'tkazib, navbatni keyingisiga surmoqchimisiz?",
        reply_markup=confirm_keyboard(
            yes_callback_data=f"admin_skip_confirm:{task_id}",
            back_callback_data=f"admin_task_menu:{task_id}",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_skip_confirm:"))
async def handle_admin_skip_confirm(callback: CallbackQuery, state: FSMContext, api_client: ApiClient) -> None:
    if callback.data is None or callback.message is None:
        return
    if not await _require_group_admin(state, callback):
        return
    task_id = int(callback.data.split(":")[1])
    user = callback.from_user
    result = await api_client.skip_queue(user.id, task_id)
    await callback.message.edit_text(
        "⏭ Navbat o'tkazib yuborildi." if result.get("success") else f"❌ {result.get('message')}"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete:"))
async def handle_admin_delete(callback: CallbackQuery, state: FSMContext, api_client: ApiClient) -> None:
    if callback.data is None or callback.message is None:
        return
    if not await _require_group_admin(state, callback):
        return
    task_id = int(callback.data.split(":")[1])
    user = callback.from_user
    result = await api_client.delete_task(user.id, task_id)
    await callback.message.edit_text(
        "🗑 Vazifa o'chirildi." if result.get("success") else f"❌ {result.get('message')}"
    )
    await callback.answer()


def _reorder_pick_keyboard(remaining: list[dict], task_id: int) -> InlineKeyboardMarkup:
    """Navbatdagi a'zoni tanlash klaviaturasi + har doim "Bekor qilish"
    tugmasi bilan - jarayonni istalgan qadamda to'xtatib, menyuga qaytish
    mumkin bo'lishi uchun."""
    picker = member_selection_keyboard(remaining, prefix="reorder_pick")
    cancel_row = [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data=f"admin_swap_cancel:{task_id}")]
    return InlineKeyboardMarkup(inline_keyboard=picker.inline_keyboard + [cancel_row])


@router.callback_query(F.data.startswith("admin_swap_start:"))
async def handle_reorder_start(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Navbat tartibini qayta belgilashdan oldin BITTA tasdiqlash so'raydi -
    darhol a'zolarni birma-bir tanlash jarayoniga o'tib ketmaslik uchun.
    """
    if callback.data is None or callback.message is None:
        return
    if not await _require_group_admin(state, callback):
        return
    task_id = int(callback.data.split(":")[1])

    await callback.message.edit_text(
        "🔄 Navbat tartibini qayta belgilamoqchimisiz? Buning uchun barcha "
        "a'zolarni birma-bir, xohlagan tartibda tanlashingiz kerak bo'ladi.",
        reply_markup=confirm_keyboard(
            yes_callback_data=f"admin_reorder_confirm:{task_id}",
            back_callback_data=f"admin_task_menu:{task_id}",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_reorder_confirm:"))
async def handle_reorder_confirm(callback: CallbackQuery, state: FSMContext, api_client: ApiClient) -> None:
    """
    Navbat tartibini QAYTA BELGILASH oqimini boshlaydi. Avval bu shunchaki
    2 ta a'zoning o'rnini almashtirar edi (swap) - agar navbatda 5 ta a'zo
    bo'lsa, faqat shu 2 tasi so'ralib, qolgan 3 tasi hech qachon so'ralmas
    edi. Endi admin BARCHA a'zolarni birma-bir, xohlagan tartibda tanlaydi -
    oxirgisi tanlanganda butun tartib bir martada saqlanadi.
    """
    if callback.data is None or callback.message is None:
        return
    if not await _require_group_admin(state, callback):
        return
    task_id = int(callback.data.split(":")[1])

    queue_result = await api_client.get_full_queue(task_id)
    entries = queue_result.get("data") or []
    if len(entries) < 2:
        await callback.message.edit_text("⚠️ Navbat tartibini o'zgartirish uchun kamida 2 ta a'zo kerak.")
        await callback.answer()
        return

    remaining = [{"member_id": e["member_id"], "full_name": e["full_name"]} for e in entries]

    await state.update_data(reorder_task_id=task_id, reorder_remaining=remaining, reorder_selected=[])
    await state.set_state(ReorderStates.waiting_for_next_member)
    await callback.message.edit_text(
        "🔄 Yangi navbat tartibini belgilaymiz.\n\n1-o'rin uchun a'zoni tanlang:",
        reply_markup=_reorder_pick_keyboard(remaining, task_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_swap_cancel:"))
async def handle_reorder_cancel(callback: CallbackQuery, state: FSMContext, api_client: ApiClient) -> None:
    if callback.data is None or callback.message is None:
        return
    task_id = int(callback.data.split(":")[1])

    data = await state.get_data()
    preserved = {k: v for k, v in data.items() if k.startswith("active_")}
    await state.clear()
    await state.set_data(preserved)

    await _show_task_menu(callback, state, api_client, task_id)
    await callback.answer("Bekor qilindi")


@router.callback_query(ReorderStates.waiting_for_next_member, F.data.startswith("reorder_pick:"))
async def handle_reorder_pick(callback: CallbackQuery, state: FSMContext, api_client: ApiClient) -> None:
    if callback.data is None or callback.message is None:
        return
    if not await _require_group_admin(state, callback):
        return
    member_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    remaining = data.get("reorder_remaining") or []
    selected = data.get("reorder_selected") or []
    task_id = data.get("reorder_task_id")

    picked = next((m for m in remaining if m["member_id"] == member_id), None)
    if picked is None:
        # Eskirgan/qayta bosilgan tugma - e'tiborsiz qoldiriladi.
        await callback.answer()
        return

    selected = selected + [picked]
    remaining = [m for m in remaining if m["member_id"] != member_id]

    if not remaining:
        # Oxirgi a'zo ham tanlandi - butun tartib bir martada saqlanadi.
        user = callback.from_user
        member_ids_in_order = [m["member_id"] for m in selected]
        result = await api_client.reorder_queue(user.id, task_id, member_ids_in_order)

        if result.get("success"):
            lines = ["✅ Yangi navbat tartibi saqlandi:\n"]
            lines += [f"{i + 1}. {m['full_name']}" for i, m in enumerate(selected)]
            text = "\n".join(lines)
        else:
            text = f"❌ {result.get('message')}"
        await callback.message.edit_text(text)

        preserved = {k: v for k, v in data.items() if k.startswith("active_")}
        await state.clear()
        await state.set_data(preserved)
        await callback.answer()
        return

    await state.update_data(reorder_remaining=remaining, reorder_selected=selected)
    await callback.message.edit_text(
        f"✅ {picked['full_name']} - {len(selected)}-o'rin.\n\n"
        f"{len(selected) + 1}-o'rin uchun a'zoni tanlang:",
        reply_markup=_reorder_pick_keyboard(remaining, task_id),
    )
    await callback.answer()


# --- Yangi vazifa yaratish (FSM oqimi) ---


@router.message(Command("newtask"))
async def handle_new_task_start(message: Message, state: FSMContext) -> None:
    group_id = await _require_active_group(message, state)
    if group_id is None:
        return
    if not await _require_group_admin(state, message):
        return
    await state.set_state(CreateTaskStates.waiting_for_name)
    await message.answer("📝 Yangi vazifa nomini kiriting (masalan, \"Oshxona tozalash\"):")


@router.message(CreateTaskStates.waiting_for_name, F.text)
async def handle_task_name(message: Message, state: FSMContext) -> None:
    await state.update_data(new_task_name=message.text.strip() if message.text else "")
    await state.set_state(CreateTaskStates.waiting_for_description)
    await message.answer("📄 Qisqacha tavsif kiriting (yoki \"-\" deb yozing, agar kerak bo'lmasa):")


@router.message(CreateTaskStates.waiting_for_description, F.text)
async def handle_task_description(message: Message, state: FSMContext) -> None:
    text = message.text.strip() if message.text else ""
    description = None if text == "-" else text
    await state.update_data(new_task_description=description)
    await state.set_state(CreateTaskStates.waiting_for_interval_days)
    await message.answer(
        "🔢 Vazifa har necha kunda takrorlanadi?\n"
        "Kunlar sonini kiriting (masalan: 1 = har kuni, 7 = har hafta, 3 = har 3 kunda):"
    )


@router.message(CreateTaskStates.waiting_for_interval_days, F.text)
async def handle_interval_days(message: Message, state: FSMContext) -> None:
    try:
        days = int(message.text.strip())
        if days < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ Iltimos, noldan katta butun son kiriting (masalan, 1 yoki 7):")
        return

    await state.update_data(new_task_interval_days=days)
    await state.set_state(CreateTaskStates.waiting_for_start_date)
    await message.answer(
        "📅 Vazifa qaysi sanadan boshlansin?\n"
        "Format: YYYY-MM-DD (masalan: 2026-07-07) yoki bugun boshlash uchun <b>bugun</b> deb yozing:"
    )


@router.message(CreateTaskStates.waiting_for_start_date, F.text)
async def handle_start_date(message: Message, state: FSMContext) -> None:
    text = message.text.strip().lower()
    state_data = await state.get_data()
    group_timezone = state_data.get("active_group_timezone", "Asia/Tashkent")

    if text == "bugun":
        start_date_str = get_local_today_in_timezone(
            timezone_str=group_timezone,
            now_utc=datetime.now(timezone.utc),
        ).isoformat()
    else:
        try:
            parsed_date = datetime.strptime(text, "%Y-%m-%d")
            start_date_str = parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            await message.answer("❌ Sana formati noto'g'ri. YYYY-MM-DD formatida kiriting (masalan, 2026-07-07) yoki 'bugun' deb yozing:")
            return

    await state.update_data(new_task_start_date=start_date_str)
    await state.set_state(CreateTaskStates.waiting_for_reminder_interval_min)
    await message.answer(
        "⏰ Eslatma necha daqiqadan keyin yuborilsin? Eng kichik qiymatni kiriting (masalan, 30):"
    )


@router.message(CreateTaskStates.waiting_for_reminder_interval_min, F.text)
async def handle_reminder_interval_min(message: Message, state: FSMContext) -> None:
    try:
        interval = int(message.text.strip()) if message.text else 0
    except ValueError:
        await message.answer("❌ Iltimos, faqat son kiriting (masalan, 30):")
        return
    if interval <= 0:
        await message.answer("❌ Interval musbat son bo'lishi kerak (masalan, 30):")
        return

    await state.update_data(new_task_reminder_min=interval)
    await state.set_state(CreateTaskStates.waiting_for_reminder_interval_max)
    await message.answer(
        "⏰ Eng katta qiymatni kiriting (masalan, 90). Eslatmalar shu ikki son orasida "
        "tasodifiy vaqtda yuboriladi:"
    )


@router.message(CreateTaskStates.waiting_for_reminder_interval_max, F.text)
async def handle_reminder_interval_max(message: Message, state: FSMContext) -> None:
    try:
        interval = int(message.text.strip()) if message.text else 0
    except ValueError:
        await message.answer("❌ Iltimos, faqat son kiriting (masalan, 90):")
        return
    if interval <= 0:
        await message.answer("❌ Interval musbat son bo'lishi kerak (masalan, 90):")
        return

    data = await state.get_data()
    reminder_min = data.get("new_task_reminder_min", 60)
    if interval < reminder_min:
        await message.answer(
            "❌ Eng katta qiymat eng kichikdan kichik bo'lmasligi kerak. Qaytadan kiriting:"
        )
        return

    await state.update_data(new_task_reminder_max=interval)
    await state.set_state(CreateTaskStates.waiting_for_reminder_start_hour)
    await message.answer(
        "🌅 Eslatmalar qaysi soatdan boshlab yuborilsin? Soatni kiriting (0-23, masalan, 8):"
    )


@router.message(CreateTaskStates.waiting_for_reminder_start_hour, F.text)
async def handle_reminder_start_hour(message: Message, state: FSMContext) -> None:
    try:
        hour = int(message.text.strip()) if message.text else -1
    except ValueError:
        await message.answer("❌ Iltimos, faqat son kiriting (masalan, 8):")
        return
    if not (0 <= hour <= 23):
        await message.answer("❌ Soat 0 dan 23 gacha bo'lishi kerak:")
        return

    await state.update_data(new_task_start_hour=hour)
    await state.set_state(CreateTaskStates.waiting_for_reminder_end_hour)
    await message.answer(
        "🌙 Eslatmalar qaysi soatgacha yuborilsin? Soatni kiriting (0-23, masalan, 22):"
    )


@router.message(CreateTaskStates.waiting_for_reminder_end_hour, F.text)
async def handle_reminder_end_hour(message: Message, state: FSMContext) -> None:
    try:
        hour = int(message.text.strip()) if message.text else -1
    except ValueError:
        await message.answer("❌ Iltimos, faqat son kiriting (masalan, 22):")
        return
    if not (0 <= hour <= 23):
        await message.answer("❌ Soat 0 dan 23 gacha bo'lishi kerak:")
        return

    data = await state.get_data()
    start_hour = data.get("new_task_start_hour", 8)
    if hour <= start_hour:
        await message.answer(
            "❌ Tugash soati boshlanish soatidan katta bo'lishi kerak. Qaytadan kiriting:"
        )
        return

    await state.update_data(new_task_end_hour=hour)
    await state.set_state(CreateTaskStates.waiting_for_photo_requirement)
    await message.answer(
        "📷 Bajarilganda rasm yuklash majburiymi?",
        reply_markup=yes_no_keyboard("require_photo"),
    )


@router.callback_query(CreateTaskStates.waiting_for_photo_requirement, F.data.startswith("require_photo:"))
async def handle_require_photo(callback: CallbackQuery, state: FSMContext, api_client: ApiClient) -> None:
    if callback.data is None or callback.message is None:
        return
    if not await _require_group_admin(state, callback):
        active_data = {k: v for k, v in (await state.get_data()).items() if k.startswith("active_")}
        await state.clear()
        await state.set_data(active_data)
        return
    require_photo = callback.data.split(":")[1] == "yes"
    data = await state.get_data()
    user = callback.from_user

    result = await api_client.create_task(
        telegram_id=user.id,
        group_id=data["active_group_id"],
        name=data["new_task_name"],
        description=data.get("new_task_description"),
        reminder_interval_min_minutes=data.get("new_task_reminder_min", 60),
        reminder_interval_max_minutes=data.get("new_task_reminder_max", 60),
        reminder_start_hour=data.get("new_task_start_hour", 8),
        reminder_end_hour=data.get("new_task_end_hour", 22),
        require_photo=require_photo,
        schedule_interval_days=data.get("new_task_interval_days", 1),
        start_date=data.get("new_task_start_date"),
    )

    if result.get("success"):
        await callback.message.answer(
            f"✅ \"{data['new_task_name']}\" vazifasi yaratildi va navbat shakllantirildi!"
        )
    else:
        await callback.message.answer(f"❌ Xatolik: {result.get('message')}")

    active_data = {k: v for k, v in data.items() if k.startswith("active_")}
    await state.clear()
    await state.set_data(active_data)
    await callback.answer()


# --- Mavjud vazifaning eslatma sozlamalarini tahrirlash (FSM oqimi) ---


@router.callback_query(F.data.startswith("edit_reminder_start:"))
async def handle_edit_reminder_start(callback: CallbackQuery, state: FSMContext, api_client: ApiClient) -> None:
    if callback.data is None or callback.message is None:
        return
    if not await _require_group_admin(state, callback):
        return

    task_id = int(callback.data.split(":")[1])
    group_id = await get_active_group_id(state)

    current_hint = ""
    if group_id is not None:
        result = await api_client.list_group_tasks(group_id)
        tasks = result.get("data") or []
        task = next((item for item in tasks if item.get("id") == task_id), None)
        if task and task.get("reminder_interval_min_minutes") is not None:
            current_hint = (
                f"\n\nJoriy sozlama: {task['reminder_interval_min_minutes']}-"
                f"{task['reminder_interval_max_minutes']} daqiqa, "
                f"{task['reminder_start_hour']}:00-{task['reminder_end_hour']}:00."
            )

    await state.update_data(edit_reminder_task_id=task_id)
    await state.set_state(EditReminderStates.waiting_for_min)
    await callback.message.answer(
        "⏰ Eslatma necha daqiqadan keyin yuborilsin? Eng kichik qiymatni kiriting "
        f"(masalan, 30):{current_hint}"
    )
    await callback.answer()


@router.message(EditReminderStates.waiting_for_min, F.text)
async def handle_edit_reminder_min(message: Message, state: FSMContext) -> None:
    try:
        interval = int(message.text.strip()) if message.text else 0
    except ValueError:
        await message.answer("❌ Iltimos, faqat son kiriting (masalan, 30):")
        return
    if interval <= 0:
        await message.answer("❌ Interval musbat son bo'lishi kerak (masalan, 30):")
        return

    await state.update_data(edit_reminder_min=interval)
    await state.set_state(EditReminderStates.waiting_for_max)
    await message.answer("⏰ Eng katta qiymatni kiriting (masalan, 90):")


@router.message(EditReminderStates.waiting_for_max, F.text)
async def handle_edit_reminder_max(message: Message, state: FSMContext) -> None:
    try:
        interval = int(message.text.strip()) if message.text else 0
    except ValueError:
        await message.answer("❌ Iltimos, faqat son kiriting (masalan, 90):")
        return
    if interval <= 0:
        await message.answer("❌ Interval musbat son bo'lishi kerak (masalan, 90):")
        return

    data = await state.get_data()
    reminder_min = data.get("edit_reminder_min", 60)
    if interval < reminder_min:
        await message.answer(
            "❌ Eng katta qiymat eng kichikdan kichik bo'lmasligi kerak. Qaytadan kiriting:"
        )
        return

    await state.update_data(edit_reminder_max=interval)
    await state.set_state(EditReminderStates.waiting_for_start_hour)
    await message.answer("🌅 Eslatmalar qaysi soatdan boshlab yuborilsin? (0-23):")


@router.message(EditReminderStates.waiting_for_start_hour, F.text)
async def handle_edit_reminder_start_hour(message: Message, state: FSMContext) -> None:
    try:
        hour = int(message.text.strip()) if message.text else -1
    except ValueError:
        await message.answer("❌ Iltimos, faqat son kiriting (masalan, 8):")
        return
    if not (0 <= hour <= 23):
        await message.answer("❌ Soat 0 dan 23 gacha bo'lishi kerak:")
        return

    await state.update_data(edit_reminder_start_hour=hour)
    await state.set_state(EditReminderStates.waiting_for_end_hour)
    await message.answer("🌙 Eslatmalar qaysi soatgacha yuborilsin? (0-23):")


@router.message(EditReminderStates.waiting_for_end_hour, F.text)
async def handle_edit_reminder_end_hour(message: Message, state: FSMContext, api_client: ApiClient) -> None:
    try:
        hour = int(message.text.strip()) if message.text else -1
    except ValueError:
        await message.answer("❌ Iltimos, faqat son kiriting (masalan, 22):")
        return
    if not (0 <= hour <= 23):
        await message.answer("❌ Soat 0 dan 23 gacha bo'lishi kerak:")
        return

    data = await state.get_data()
    start_hour = data.get("edit_reminder_start_hour", 8)
    if hour <= start_hour:
        await message.answer(
            "❌ Tugash soati boshlanish soatidan katta bo'lishi kerak. Qaytadan kiriting:"
        )
        return

    user = message.from_user
    result = await api_client.update_task(
        telegram_id=user.id,
        task_id=data["edit_reminder_task_id"],
        reminder_interval_min_minutes=data.get("edit_reminder_min", 60),
        reminder_interval_max_minutes=data.get("edit_reminder_max", 60),
        reminder_start_hour=start_hour,
        reminder_end_hour=hour,
    )

    if result.get("success"):
        await message.answer("✅ Eslatma sozlamalari yangilandi.")
    else:
        await message.answer(f"❌ Xatolik: {result.get('message')}")

    active_data = {k: v for k, v in data.items() if k.startswith("active_")}
    await state.clear()
    await state.set_data(active_data)


@router.message(Command("members"))
async def handle_members(message: Message, state: FSMContext, api_client: ApiClient) -> None:
    group_id = await _require_active_group(message, state)
    if group_id is None:
        return

    result = await api_client.list_members(group_id)
    members = result.get("data") or []
    lines = ["👥 <b>Guruh a'zolari:</b>"]
    for m in members:
        role_icon = "👑" if m["role"] == "admin" else "👤"
        vacation_icon = " 🏖 (dam olishda)" if m["is_on_vacation"] else ""
        lines.append(f"{role_icon} {m['full_name']}{vacation_icon} (id: {m['member_id']})")
    await message.answer("\n".join(lines))


@router.message(Command("vacation"))
async def handle_vacation_start(message: Message, state: FSMContext, api_client: ApiClient) -> None:
    """/vacation <member_id> - shu a'zoni dam olish rejimiga o'tkazadi/qaytaradi."""
    group_id = await _require_active_group(message, state)
    if group_id is None:
        return
    if not await _require_group_admin(state, message):
        return

    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        result = await api_client.list_members(group_id)
        members = result.get("data") or []
        lines = ["Foydalanish: <code>/vacation [member_id]</code>\n\nA'zolar:"]
        for m in members:
            lines.append(f"  {m['member_id']} - {m['full_name']}")
        await message.answer("\n".join(lines))
        return

    member_id = int(parts[1])
    members_result = await api_client.list_members(group_id)
    member = next((m for m in (members_result.get("data") or []) if m["member_id"] == member_id), None)
    new_state = not member["is_on_vacation"] if member else True

    user = message.from_user
    result = await api_client.set_vacation(user.id, member_id, new_state)
    await message.answer(
        result.get("message", "Bajarildi") if result.get("success") else f"❌ {result.get('message')}"
    )


@router.message(Command("setadmin"))
async def handle_setadmin(message: Message, state: FSMContext, api_client: ApiClient) -> None:
    """
    /setadmin <member_id> - shu a'zoni admin qiladi yoki (admin bo'lsa) oddiy
    a'zoga tushiradi. Guruh yaratuvchisi bilan cheklanmagan - istalgan mavjud
    admin boshqa a'zolarni ham admin qila oladi, shunda vazifalarni
    yaratish/tahrirlash huquqi faqat "guruh egasi"ga emas, balki barcha
    tayinlangan adminlarga tegishli bo'ladi.
    """
    group_id = await _require_active_group(message, state)
    if group_id is None:
        return
    if not await _require_group_admin(state, message):
        return

    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        result = await api_client.list_members(group_id)
        members = result.get("data") or []
        lines = ["Foydalanish: <code>/setadmin [member_id]</code>\n\nA'zolar:"]
        for m in members:
            role_icon = "👑" if m["role"] == "admin" else "👤"
            lines.append(f"  {m['member_id']} - {role_icon} {m['full_name']}")
        await message.answer("\n".join(lines))
        return

    member_id = int(parts[1])
    members_result = await api_client.list_members(group_id)
    member = next((m for m in (members_result.get("data") or []) if m["member_id"] == member_id), None)
    if member is None:
        await message.answer("❌ A'zo topilmadi")
        return
    new_role = "member" if member["role"] == "admin" else "admin"

    user = message.from_user
    result = await api_client.set_member_role(user.id, group_id, member_id, new_role)
    if not result.get("success"):
        await message.answer(f"❌ {result.get('message')}")
        return

    icon = "👑" if new_role == "admin" else "👤"
    role_label = "admin" if new_role == "admin" else "oddiy a'zo"
    await message.answer(f"{icon} {member['full_name']} endi {role_label}")


@router.message(Command("deletetask"))
async def handle_list_tasks_for_delete(message: Message, state: FSMContext, api_client: ApiClient) -> None:
    group_id = await _require_active_group(message, state)
    if group_id is None:
        return
    if not await _require_group_admin(state, message):
        return

    result = await api_client.list_group_tasks(group_id)
    tasks = result.get("data") or []
    if not tasks:
        await message.answer("Vazifalar topilmadi.")
        return

    await message.answer(
        "🗑 O'chirmoqchi bo'lgan vazifangizni tanlang:",
        reply_markup=task_list_keyboard(tasks, action_prefix="delete_task_select"),
    )


@router.callback_query(F.data.startswith("delete_task_select:"))
async def handle_delete_task_callback(callback: CallbackQuery, state: FSMContext, api_client: ApiClient) -> None:
    if callback.data is None or callback.message is None:
        return
    if not await _require_group_admin(state, callback):
        return
    task_id = int(callback.data.split(":")[1])
    user = callback.from_user

    result = await api_client.delete_task(telegram_id=user.id, task_id=task_id)
    if result.get("success"):
        await callback.message.edit_text("🗑 Vazifa muvaffaqiyatli o'chirildi.")
    else:
        await callback.message.edit_text(f"❌ Xatolik: {result.get('message') or 'O\'chirish muvaffaqiyatsiz tugadi'}")
    await callback.answer()
