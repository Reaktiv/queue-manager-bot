"""
Bot uchun inline klaviaturalar.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def group_selection_keyboard(groups: list) -> InlineKeyboardMarkup:
    """
    Foydalanuvchiga guruhlarini tanlash uchun inline tugmalar yasab beradi.
    UUID (64 baytlik cheklov) xavfsizligi hisobga olingan.
    """
    builder = InlineKeyboardBuilder()

    for group in groups:
        # group["id"] UUID string bo'lsa (masalan: '4f9e31b2-7a8c...')
        # 'select_group:4f9e31b2-7a8c...' jami ~45 bayt bo'ladi, bu 64 baytlik limitga to'liq sig'adi.
        group_id = str(group["id"])
        group_name = group.get("name", f"Guruh {group_id[:8]}")

        builder.button(
            text=f"🏠 {group_name}",
            callback_data=f"select_group:{group_id}"
        )

    # Tugmalarni 1 qatordan tartiblaymiz
    builder.adjust(1)
    return builder.as_markup()

def task_list_keyboard(tasks: list[dict], action_prefix: str = "task") -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"📋 {t['name']}", callback_data=f"{action_prefix}:{t['id']}")]
        for t in tasks
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def task_action_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Bajarildi", callback_data=f"complete:{task_id}")],
            [InlineKeyboardButton(text="👀 Navbatni ko'rish", callback_data=f"preview:{task_id}")],
            [InlineKeyboardButton(text="👥 Hozirgi navbatlar", callback_data="view_turns")],
        ]
    )


def future_task_action_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👀 Navbatni ko'rish", callback_data=f"preview:{task_id}")],
            [InlineKeyboardButton(text="👥 Hozirgi navbatlar", callback_data="view_turns")],
        ]
    )


def turns_view_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Hozirgi navbatlar", callback_data="view_turns")]
        ]
    )


def admin_task_menu_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👀 Navbat", callback_data=f"preview:{task_id}")],
            [InlineKeyboardButton(text="⏭ Skip", callback_data=f"admin_skip:{task_id}")],
            [InlineKeyboardButton(text="🔄 Swap", callback_data=f"admin_swap_start:{task_id}")],
            [InlineKeyboardButton(text="⏰ Eslatma sozlamalari", callback_data=f"edit_reminder_start:{task_id}")],
        ]
    )






def yes_no_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha", callback_data=f"{prefix}:yes"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data=f"{prefix}:no"),
            ]
        ]
    )


def completion_vote_keyboard(
    completion_id: int, yes_count: int = 0, no_count: int = 0
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"✅ Ha ({yes_count})", callback_data=f"vote_yes:{completion_id}"
                ),
                InlineKeyboardButton(
                    text=f"❌ Yo'q ({no_count})", callback_data=f"vote_no:{completion_id}"
                ),
            ]
        ]
    )


def member_selection_keyboard(members: list[dict], prefix: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{m['full_name']}" + (" 🏖" if m.get("is_on_vacation") else ""),
                callback_data=f"{prefix}:{m['member_id']}",
            )
        ]
        for m in members
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
