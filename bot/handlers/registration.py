"""
Foydalanuvchi ro'yxatdan o'tish va guruhga qo'shilish handlerlari.
"""
import structlog
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from i18n.translator import t
from keyboards.reply import main_menu_keyboard
from services.api_client import ApiClient
from states.fsm import CreateGroupStates, JoinGroupStates

logger = structlog.get_logger()
router = Router(name="registration")


def _lang(user) -> str:
    return (user.language_code or "uz").split("-")[0]


@router.message(CommandStart())
async def handle_start(message: Message, api_client: ApiClient) -> None:
    """
    Foydalanuvchi /start bosganda:
    1. Agar ro'yxatda bo'lmasa - avtomatik ro'yxatga oladi (telegram_id asosiy kalit).
    2. Xush kelibsiz xabari + asosiy menyu (foydalanuvchi tilida).
    """
    user = message.from_user
    if user is None:
        return

    lang = _lang(user)
    await api_client.register_user(
        telegram_id=user.id,
        full_name=f"{user.first_name} {user.last_name or ''}".strip(),
        username=user.username,
        language=lang,
    )

    # Doimiy pastki menyu DARHOL ko'rsatiladi - foydalanuvchi har safar
    # Mini App'ga kirmasdan ham Profil/vazifalar/yordamga bir bosishda
    # o'ta oladi. Telefon raqami so'ralishi BU YERDA emas - u faqat
    # "Profil" ochilganda (agar hali ulashilmagan bo'lsa) so'raladi
    # (handlers/profile.py), shunda /start darhol to'liq menyu bilan
    # yakunlanadi, oraliq "raqam ulashasizmi?" bosqichi bilan kechikmaydi.
    await message.answer(
        t("welcome", lang=lang, name=user.first_name), reply_markup=main_menu_keyboard()
    )


@router.message(Command("join"))
async def handle_join_command(message: Message, state: FSMContext) -> None:
    lang = _lang(message.from_user) if message.from_user else "uz"
    await message.answer(t("ask_invite_code", lang=lang))
    await state.set_state(JoinGroupStates.waiting_for_invite_code)


@router.message(JoinGroupStates.waiting_for_invite_code, F.text)
async def handle_invite_code(message: Message, state: FSMContext, api_client: ApiClient) -> None:
    invite_code = message.text.strip().upper() if message.text else ""
    user = message.from_user
    if user is None:
        return
    lang = _lang(user)

    result = await api_client.join_group(telegram_id=user.id, invite_code=invite_code)
    await state.clear()

    if result.get("success"):
        group_name = result["data"]["group_name"]

        # Yangi qo'shilgan guruhni avtomatik "faol guruh" qilib belgilaymiz
        groups_result = await api_client.list_my_groups(user.id)
        matched = next(
            (g for g in (groups_result.get("data") or []) if g["name"] == group_name), None
        )
        if matched:
            await state.update_data(
                active_group_id=matched["id"],
                active_group_name=matched["name"],
                active_member_role=matched["role"],
                active_member_id=matched["member_id"],
            )

        await message.answer(
            t("joined_group", lang=lang, group_name=group_name)
            + "\n\n🙋 /mytasks"
        )
    else:
        await message.answer(result.get("message") or t("invalid_invite_code", lang=lang))


@router.message(Command("creategroup"))
async def handle_create_group_command(message: Message, state: FSMContext) -> None:
    lang = _lang(message.from_user) if message.from_user else "uz"
    await message.answer(t("ask_group_name", lang=lang))
    await state.set_state(CreateGroupStates.waiting_for_name)


@router.message(CreateGroupStates.waiting_for_name, F.text)
async def handle_group_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip() if message.text else ""
    user = message.from_user
    if user is None or not name:
        await state.clear()
        return
    lang = _lang(user)
    await state.update_data(new_group_name=name)
    await state.set_state(CreateGroupStates.waiting_for_chat_id)
    await message.answer(
        "🆔 Guruhga eslatma yuboriladigan Telegram group ID ni kiriting.\n"
        "Masalan: <code>-1001234567890</code>\n"
        "Agar hozircha bog'lamoqchi bo'lmasangiz, <code>-</code> deb yozing."
    )


@router.message(CreateGroupStates.waiting_for_chat_id, F.text)
async def handle_group_chat_id(message: Message, state: FSMContext, api_client: ApiClient) -> None:
    text = message.text.strip() if message.text else ""
    user = message.from_user
    if user is None:
        await state.clear()
        return
    lang = _lang(user)
    data = await state.get_data()
    name = data.get("new_group_name")
    if not name:
        await state.clear()
        await message.answer("❌ Guruh nomi topilmadi. Qaytadan /creategroup qiling.")
        return

    telegram_chat_id: int | None = None
    if text != "-":
        try:
            telegram_chat_id = int(text)
        except ValueError:
            await message.answer(
                "❌ Group ID noto'g'ri. Butun son kiriting "
                "(masalan, <code>-1001234567890</code>) yoki <code>-</code> yuboring."
            )
            return

    result = await api_client.create_group(
        telegram_id=user.id,
        name=name,
        telegram_chat_id=telegram_chat_id,
    )

    if result.get("success") and "data" in result:
        group_id = result["data"].get("group_id")
        invite_code = result["data"].get("invite_code")

        # Backend to'g'ridan-to'g'ri yaratuvchining member_id sini qaytargan bo'lsa, o'shani olamiz
        member_id = result["data"].get("member_id")

        # 2. Agar backend member_id ni qaytarmagan bo'lsa, bazani qayta tekshiramiz
        if not member_id:
            try:
                groups_result = await api_client.list_my_groups(user.id)
                if groups_result.get("success") and "data" in groups_result:
                    matched = next((g for g in groups_result["data"] if str(g["id"]) == str(group_id)), None)
                    if matched:
                        member_id = matched.get("member_id")
            except Exception as e:
                logger.error("Guruh a'zoligini qayta tekshirishda xatolik", error=str(e))

        # 3. FSM State'ni xavfsiz yangilash
        await state.update_data(
            active_group_id=group_id,
            active_group_name=name,
            active_member_role="admin",
            active_member_id=member_id,
            active_group_telegram_chat_id=telegram_chat_id,
        )

        # Guruh yaratish holatidan chiqamiz
        await state.set_state(None)

        await message.answer(
            t("group_created", lang=lang, name=name, invite_code=invite_code)
            + (
                "\n\n📣 Guruh chat ID saqlandi. Endi reminderlar shu chatga ham yuboriladi."
                if telegram_chat_id is not None
                else "\n\nℹ️ Group ID saqlanmadi. Keyinroq /link bilan bog'lashingiz mumkin."
            )
            + "\n\n📝 /newtask"
        )
    else:
        # Agar backend aniq bir xato xabari qaytargan bo'lsa, o'shani ko'rsatamiz
        error_msg = result.get("message") or t("invalid_invite_code", lang=lang)
        await message.answer(f"❌ {error_msg}")
        await state.clear()
