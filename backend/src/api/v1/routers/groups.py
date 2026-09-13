"""
Presentation Layer: Guruh yaratish va qo'shilish endpointlari.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ....api.auth_deps import (
    Identity,
    ensure_actor_can_access_group,
    ensure_actor_owns_telegram_id,
    ensure_admin_for_group,
    verify_bot_or_mini_app,
)
from ....api.deps import get_group_service, get_user_service, get_session
from ....infrastructure.models.group import MemberRole
from ....services.group_service import (
    AlreadyMemberError,
    DuplicateGroupChatIdError,
    GroupService,
    InvalidInviteCodeError,
    LastAdminError,
    MemberNotFoundError,
)
from ....services.user_service import UserService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/groups", tags=["Groups"], dependencies=[Depends(verify_bot_or_mini_app)]
)


class ApiResponse(BaseModel):
    success: bool
    data: object | None = None
    message: str | None = None


class CreateGroupRequest(BaseModel):
    telegram_id: int
    name: str = Field(min_length=1, max_length=255)
    timezone: str = "Asia/Tashkent"
    telegram_chat_id: int | None = None


class VacationRequest(BaseModel):
    telegram_id: int
    member_id: int
    is_on_vacation: bool


class SetRoleRequest(BaseModel):
    telegram_id: int
    role: str = Field(pattern="^(admin|member)$")


class JoinGroupRequest(BaseModel):
    telegram_id: int
    invite_code: str = Field(min_length=4, max_length=16)


@router.get("/user/{telegram_id}", response_model=ApiResponse)
async def list_my_groups(
    telegram_id: int,
    session: AsyncSession = Depends(get_session),
    group_service: GroupService = Depends(get_group_service),
    user_service: UserService = Depends(get_user_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    await ensure_actor_owns_telegram_id(identity, telegram_id, session)
    user = await user_service.get_by_telegram_id(telegram_id)
    if user is None:
        return ApiResponse(success=False, message="Foydalanuvchi topilmadi")

    rows = await group_service.list_groups_for_user(user.id)
    data = [
        {
            "id": group.id,
            "name": group.name,
            "role": member.role.value,
            "member_id": member.id,
            "timezone": group.timezone,
        }
        for group, member in rows
    ]
    return ApiResponse(success=True, data=data)


@router.get("/{group_id}/members", response_model=ApiResponse)
async def list_members(
    group_id: int,
    session: AsyncSession = Depends(get_session),
    group_service: GroupService = Depends(get_group_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    await ensure_actor_can_access_group(identity, group_id, session)
    members = await group_service.list_members(group_id)
    data = [
        {
            "member_id": m.id,
            "user_id": m.user_id,
            "full_name": m.user.full_name if m.user else None,
            "role": m.role.value,
            "is_on_vacation": m.is_on_vacation,
        }
        for m in members
    ]
    return ApiResponse(success=True, data=data)


@router.post("/vacation", response_model=ApiResponse)
async def set_vacation(
    payload: VacationRequest,
    session: AsyncSession = Depends(get_session),
    group_service: GroupService = Depends(get_group_service),
    user_service: UserService = Depends(get_user_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    """Admin biror a'zoni vaqtincha dam olish (vacation) rejimiga qo'yadi/qaytaradi."""
    await ensure_actor_owns_telegram_id(identity, payload.telegram_id, session)
    user = await user_service.get_by_telegram_id(payload.telegram_id)
    if user is None:
        return ApiResponse(success=False, message="Avval /start orqali ro'yxatdan o'ting")

    member = await group_service.get_member_by_id(payload.member_id)
    if member is None:
        return ApiResponse(success=False, message="A'zo topilmadi")

    await ensure_admin_for_group(user.id, member.group_id, session)

    await group_service.set_vacation(payload.member_id, payload.is_on_vacation)
    status_text = (
        "dam olish rejimiga qo'yildi" if payload.is_on_vacation else "faol holatga qaytarildi"
    )
    return ApiResponse(success=True, message=f"A'zo {status_text}")


@router.patch("/{group_id}/members/{member_id}/role", response_model=ApiResponse)
async def set_member_role(
    group_id: int,
    member_id: int,
    payload: SetRoleRequest,
    session: AsyncSession = Depends(get_session),
    group_service: GroupService = Depends(get_group_service),
    user_service: UserService = Depends(get_user_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    """
    A'zoni ADMIN yoki oddiy MEMBER qiladi. Faqat mavjud guruh adminlari
    (guruh yaratuvchisi bilan cheklanmagan holda) bajara oladi - shu orqali
    vazifa yaratish/tahrirlash huquqi faqat "guruh egasi"da emas, balki
    barcha tayinlangan adminlarda bo'ladi.
    """
    await ensure_actor_owns_telegram_id(identity, payload.telegram_id, session)
    user = await user_service.get_by_telegram_id(payload.telegram_id)
    if user is None:
        return ApiResponse(success=False, message="Foydalanuvchi topilmadi")

    await ensure_admin_for_group(user.id, group_id, session)

    role = MemberRole.ADMIN if payload.role == "admin" else MemberRole.MEMBER
    try:
        member = await group_service.set_member_role(group_id, member_id, role)
    except MemberNotFoundError:
        return ApiResponse(success=False, message="A'zo topilmadi")
    except LastAdminError:
        return ApiResponse(
            success=False,
            message="Guruhning yagona adminini oddiy a'zoga tushirib bo'lmaydi",
        )

    return ApiResponse(
        success=True,
        data={"member_id": member.id, "role": member.role.value},
        message="A'zo yangilandi" if role == MemberRole.MEMBER else "A'zo admin qilindi",
    )


@router.post("/create", response_model=ApiResponse)
async def create_group(
    payload: CreateGroupRequest,
    session: AsyncSession = Depends(get_session),
    group_service: GroupService = Depends(get_group_service),
    user_service: UserService = Depends(get_user_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    await ensure_actor_owns_telegram_id(identity, payload.telegram_id, session)
    user = await user_service.get_by_telegram_id(payload.telegram_id)
    if user is None:
        return ApiResponse(success=False, message="Avval /start orqali ro'yxatdan o'ting")

    try:
        group = await group_service.create_group(
            name=payload.name,
            created_by_user_id=user.id,
            timezone=payload.timezone,
            telegram_chat_id=payload.telegram_chat_id,
        )
    except DuplicateGroupChatIdError:
        return ApiResponse(
            success=False,
            message="Bu Telegram group ID allaqachon boshqa guruhga bog'langan",
        )
    return ApiResponse(
        success=True,
        data={
            "group_id": group.id,
            "group_name": group.name,
            "invite_code": group.invite_code,
            "telegram_chat_id": group.telegram_chat_id,
        },
        message="Guruh yaratildi",
    )


@router.post("/join", response_model=ApiResponse)
async def join_group(
    payload: JoinGroupRequest,
    session: AsyncSession = Depends(get_session),
    group_service: GroupService = Depends(get_group_service),
    user_service: UserService = Depends(get_user_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    await ensure_actor_owns_telegram_id(identity, payload.telegram_id, session)
    user = await user_service.get_by_telegram_id(payload.telegram_id)
    if user is None:
        return ApiResponse(success=False, message="Avval /start orqali ro'yxatdan o'ting")

    try:
        member = await group_service.join_by_invite_code(
            user_id=user.id, invite_code=payload.invite_code
        )
    except InvalidInviteCodeError:
        return ApiResponse(success=False, message="Taklif kodi noto'g'ri yoki guruh faol emas")
    except AlreadyMemberError:
        return ApiResponse(success=False, message="Siz allaqachon shu guruh a'zosisiz")

    group = await group_service.get_group_by_invite_code(payload.invite_code)
    return ApiResponse(
        success=True,
        data={"member_id": member.id, "group_name": group.name if group else ""},
        message="Guruhga muvaffaqiyatli qo'shildingiz",
    )


class LinkGroupByCodeRequest(BaseModel):
    telegram_id: int
    invite_code: str
    telegram_chat_id: int


@router.post("/link-by-code", response_model=ApiResponse)
async def link_group_by_code(
    payload: LinkGroupByCodeRequest,
    session: AsyncSession = Depends(get_session),
    group_service: GroupService = Depends(get_group_service),
    user_service: UserService = Depends(get_user_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    await ensure_actor_owns_telegram_id(identity, payload.telegram_id, session)
    user = await user_service.get_by_telegram_id(payload.telegram_id)
    if user is None:
        return ApiResponse(success=False, message="Foydalanuvchi topilmadi")

    group = await group_service.get_group_by_invite_code(payload.invite_code)
    if group is None:
        return ApiResponse(success=False, message="Guruh topilmadi yoki faol emas")

    # Verify admin status
    await ensure_admin_for_group(user.id, group.id, session)

    try:
        await group_service.set_telegram_chat_id(group.id, payload.telegram_chat_id)
    except DuplicateGroupChatIdError:
        return ApiResponse(
            success=False,
            message="Bu Telegram group ID allaqachon boshqa guruhga bog'langan",
        )
    await session.commit()

    return ApiResponse(
        success=True,
        data={"group_id": group.id, "group_name": group.name},
        message="Guruh muvaffaqiyatli bog'landi",
    )


class BroadcastRequest(BaseModel):
    telegram_id: int
    message: str = Field(min_length=1)


@router.post("/{group_id}/broadcast", response_model=ApiResponse)
async def broadcast_message(
    group_id: int,
    payload: BroadcastRequest,
    session: AsyncSession = Depends(get_session),
    group_service: GroupService = Depends(get_group_service),
    user_service: UserService = Depends(get_user_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    await ensure_actor_owns_telegram_id(identity, payload.telegram_id, session)
    user = await user_service.get_by_telegram_id(payload.telegram_id)
    if user is None:
        return ApiResponse(success=False, message="Foydalanuvchi topilmadi")

    # Verify admin status
    await ensure_admin_for_group(user.id, group_id, session)

    group = await group_service._repo.get_by_id(group_id)
    if group is None:
        return ApiResponse(success=False, message="Guruh topilmadi")

    from ....repositories.notification_repository import NotificationTemplateRepository
    from ....services.notification_service import NotificationService

    notification_service = NotificationService(NotificationTemplateRepository(session))

    # Send to group chat
    if group.telegram_chat_id:
        try:
            await notification_service.send_group_message(group.telegram_chat_id, payload.message)
        except Exception:
            pass

    # Send to all members in private chat
    members = await group_service._repo.list_members(group_id)
    for member in members:
        member_user = await user_service._repo.get_by_id(member.user_id)
        if member_user and member_user.telegram_id:
            try:
                await notification_service.send_private_message(member_user.telegram_id, payload.message)
            except Exception:
                pass

    return ApiResponse(success=True, message="Xabar barchaga yuborildi")
