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
            [InlineKeyboardButton(text="✅ Bajarish", callback_data=f"complete:{task_id}")],
            [InlineKeyboardButton(text="👀 Navbatni ko'rish", callback_data=f"preview:{task_id}")],
            [InlineKeyboardButton(text="👥 Hozirgi navbatlar", callback_data="view_turns")],
        ]
    )


def future_task_action_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Oldindan bajarish", callback_data=f"complete:{task_id}")],
            [InlineKeyboardButton(text="👀 Navbatni ko'rish", callback_data=f"preview:{task_id}")],
            [InlineKeyboardButton(text="👥 Hozirgi navbatlar", callback_data="view_turns")],
        ]
    )


def early_completion_confirm_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Muddat hali kelmagan vazifani bajarishni tasdiqlash so'raladi."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Ha, bajaraman", callback_data=f"confirm_early:{task_id}:yes")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"confirm_early:{task_id}:no")],
        ]
    )


def ask_photo_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Rasm so'ralayotganda foydalanuvchi orqaga qaytib fikridan qaytishi mumkin."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"cancel_complete:{task_id}")],
        ]
    )


def turns_view_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Hozirgi navbatlar", callback_data="view_turns")]
        ]
    )


def confirm_keyboard(
    yes_callback_data: str, back_callback_data: str, yes_text: str = "✅ Ha"
) -> InlineKeyboardMarkup:
    """Har qanday amaldan oldin bitta tasdiqlash so'rash uchun umumiy
    klaviatura: "Ha" va "Orqaga" tugmalari."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=yes_text, callback_data=yes_callback_data)],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data=back_callback_data)],
        ]
    )


def admin_task_menu_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👀 Navbat", callback_data=f"preview:{task_id}")],
            [InlineKeyboardButton(text="⏭ Skip", callback_data=f"admin_skip:{task_id}")],
            [InlineKeyboardButton(text="🔄 Navbatni qayta tartiblash", callback_data=f"admin_swap_start:{task_id}")],
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


def completion_vote_keyboard(completion_id: int) -> InlineKeyboardMarkup:
    """
    Bajarilgan vazifani guruh a'zolari ✅/❌ ovoz berib tasdiqlashi (yoki
    rad etishi) uchun tugmalar. Bajaruvchidan tashqari faol a'zolarning
    yarmidan ko'pi "Ha" desa - navbat keyingi a'zoga o'tadi; yarmidan
    ko'pi "Yo'q" desa - vazifa shu a'zoda qoladi. Ko'pchilik hosil
    bo'lguncha (yoki 2 soatlik muddat tugaguncha) tugmalar doimiy qoladi -
    bir nechta kishi ovoz bera olishi kerak.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha", callback_data=f"vote:{completion_id}:yes"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data=f"vote:{completion_id}:no"),
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
