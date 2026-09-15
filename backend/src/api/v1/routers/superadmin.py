"""
Presentation Layer: Super Admin (Bot Owner) uchun global boshqaruv endpointlari.

Barcha endpointlar JWT orqali autentifikatsiya qilingan va foydalanuvchi
`is_super_admin=True` bo'lishini talab qiladi (guruh a'zoligidan mustaqil).
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ....api.auth_deps import CurrentUser, require_super_admin
from ....services.super_admin_service import SuperAdminService
from ....api.deps import get_super_admin_service

router = APIRouter(prefix="/superadmin", tags=["Super Admin"])


class ApiResponse(BaseModel):
    success: bool
    data: object | None = None
    message: str | None = None


class BroadcastRequest(BaseModel):
    text: str


class MaintenanceModeRequest(BaseModel):
    enabled: bool


@router.get("/groups", response_model=ApiResponse)
async def list_all_groups(
    _admin: CurrentUser = Depends(require_super_admin),
    service: SuperAdminService = Depends(get_super_admin_service),
):
    data = await service.list_all_groups_with_stats()
    return ApiResponse(success=True, data=data)


@router.get("/users", response_model=ApiResponse)
async def list_all_users(
    _admin: CurrentUser = Depends(require_super_admin),
    service: SuperAdminService = Depends(get_super_admin_service),
):
    data = await service.list_all_users()
    return ApiResponse(success=True, data=data)


@router.get("/users/{user_id}/profile", response_model=ApiResponse)
async def get_user_profile(
    user_id: int,
    _admin: CurrentUser = Depends(require_super_admin),
    service: SuperAdminService = Depends(get_super_admin_service),
):
    """
    "Userlar" ro'yxatidagi biror foydalanuvchiga bosilganda to'liq
    profilini ko'rsatish uchun - a'zo bo'lgan guruhlar bilan.
    `user_id` - `User.id` (`/superadmin/users` ro'yxatidagi `id` maydoni).
    """
    data = await service.get_user_profile(user_id)
    if data is None:
        return ApiResponse(success=False, message="Foydalanuvchi topilmadi")
    return ApiResponse(success=True, data=data)


@router.get("/stats", response_model=ApiResponse)
async def get_system_stats(
    _admin: CurrentUser = Depends(require_super_admin),
    service: SuperAdminService = Depends(get_super_admin_service),
):
    data = await service.get_system_stats()
    return ApiResponse(success=True, data=data)


@router.post("/maintenance-mode", response_model=ApiResponse)
async def set_maintenance_mode(
    payload: MaintenanceModeRequest,
    admin: CurrentUser = Depends(require_super_admin),
    service: SuperAdminService = Depends(get_super_admin_service),
):
    await service.set_maintenance_mode(payload.enabled, admin.user_id)
    state = "yoqildi" if payload.enabled else "o'chirildi"
    return ApiResponse(success=True, message=f"Maintenance mode {state}")


@router.post("/broadcast", response_model=ApiResponse)
async def broadcast_message(
    payload: BroadcastRequest,
    admin: CurrentUser = Depends(require_super_admin),
    service: SuperAdminService = Depends(get_super_admin_service),
):
    result = await service.broadcast_message(payload.text, admin.user_id)
    return ApiResponse(
        success=True,
        data=result,
        message=f"{result['sent']}/{result['total']} foydalanuvchiga yuborildi",
    )


@router.get("/logs", response_model=ApiResponse)
async def list_error_logs(
    _admin: CurrentUser = Depends(require_super_admin),
    service: SuperAdminService = Depends(get_super_admin_service),
):
    data = await service.list_recent_error_logs()
    return ApiResponse(success=True, data=data)


@router.delete("/logs", response_model=ApiResponse)
async def clear_error_logs(
    admin: CurrentUser = Depends(require_super_admin),
    service: SuperAdminService = Depends(get_super_admin_service),
):
    """Barcha xato yozuvlarini o'chiradi. Qaytarib bo'lmaydigan amal."""
    deleted_count = await service.clear_error_logs(admin.user_id)
    return ApiResponse(
        success=True,
        data={"deleted_count": deleted_count},
        message=f"{deleted_count} ta yozuv o'chirildi",
    )
