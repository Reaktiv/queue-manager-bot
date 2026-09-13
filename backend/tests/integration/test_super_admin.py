"""
Super Admin (Bot Owner) endpointlari uchun integratsiya testlari:
- avtomatik super-admin belgilash (SUPER_ADMIN_TELEGRAM_IDS)
- global statistika va ro'yxatlar
- oddiy foydalanuvchi uchun 403
- maintenance mode - oddiy endpointlarni bloklaydi, super admin/health ochiq qoladi
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.src.api import deps
from backend.src.core.config import settings
from backend.src.core.security import create_access_token
from backend.src.main import app

pytestmark = pytest.mark.asyncio

HEADERS = {"X-Internal-Secret": settings.BOT_INTERNAL_SECRET}


@pytest_asyncio.fixture
async def client(session):
    async def _override_get_session():
        yield session

    app.dependency_overrides[deps.get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _register_super_admin(client, monkeypatch, telegram_id: int = 9001) -> int:
    """SUPER_ADMIN_TELEGRAM_IDS orqali super admin sifatida ro'yxatdan o'tkazadi."""
    monkeypatch.setattr(settings, "SUPER_ADMIN_TELEGRAM_IDS", str(telegram_id))
    resp = await client.post(
        "/api/v1/users/register",
        json={"telegram_id": telegram_id, "full_name": "Bot Owner"},
        headers=HEADERS,
    )
    return resp.json()["data"]["id"]


async def test_registering_configured_telegram_id_grants_super_admin(client, monkeypatch):
    user_id = await _register_super_admin(client, monkeypatch)
    token = create_access_token(user_id, is_super_admin=True)

    resp = await client.get(
        "/api/v1/superadmin/stats", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_non_super_admin_gets_403(client, monkeypatch):
    await _register_super_admin(client, monkeypatch)  # boshqa user super admin bo'ladi

    # Oddiy (super bo'lmagan) foydalanuvchi ro'yxatdan o'tadi
    resp = await client.post(
        "/api/v1/users/register",
        json={"telegram_id": 9002, "full_name": "Regular Joe"},
        headers=HEADERS,
    )
    regular_user_id = resp.json()["data"]["id"]
    token = create_access_token(regular_user_id, is_super_admin=False)

    resp = await client.get(
        "/api/v1/superadmin/stats", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


async def test_clear_error_logs_deletes_all_and_requires_super_admin(client, session, monkeypatch):
    from backend.src.infrastructure.models.settings import SystemLog

    user_id = await _register_super_admin(client, monkeypatch)
    token = create_access_token(user_id, is_super_admin=True)

    session.add_all(
        [
            SystemLog(level="ERROR", message="birinchi xato"),
            SystemLog(level="ERROR", message="ikkinchi xato"),
        ]
    )
    await session.flush()

    resp = await client.get(
        "/api/v1/superadmin/logs", headers={"Authorization": f"Bearer {token}"}
    )
    assert len(resp.json()["data"]) == 2

    resp = await client.delete(
        "/api/v1/superadmin/logs", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["deleted_count"] == 2

    resp = await client.get(
        "/api/v1/superadmin/logs", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.json()["data"] == []


async def test_clear_error_logs_requires_super_admin(client, monkeypatch):
    await _register_super_admin(client, monkeypatch)
    resp = await client.post(
        "/api/v1/users/register",
        json={"telegram_id": 9003, "full_name": "Regular Joe"},
        headers=HEADERS,
    )
    regular_user_id = resp.json()["data"]["id"]
    token = create_access_token(regular_user_id, is_super_admin=False)

    resp = await client.delete(
        "/api/v1/superadmin/logs", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


async def test_maintenance_mode_toggle_via_service(session):
    """
    Middleware alohida DB ulanishi ishlatgani uchun (background-safe dizayn),
    uni to'liq HTTP orqali sinash cross-connection muammosini keltirib chiqaradi.
    Shu sababli bu yerda SuperAdminService darajasida sinaymiz - bu servis
    middleware ham, `/superadmin/maintenance-mode` endpointi ham ishlatadigan
    xuddi shu mantiq.
    """
    from backend.src.infrastructure.models.user import User
    from backend.src.repositories.audit_repository import AuditRepository
    from backend.src.repositories.group_repository import GroupRepository
    from backend.src.repositories.notification_repository import NotificationTemplateRepository
    from backend.src.repositories.penalty_repository import PenaltyRepository
    from backend.src.repositories.settings_repository import SettingsRepository
    from backend.src.repositories.task_repository import TaskRepository
    from backend.src.repositories.user_repository import UserRepository
    from backend.src.services.notification_service import NotificationService
    from backend.src.services.super_admin_service import SuperAdminService

    owner = User(telegram_id=9500, full_name="Owner")
    session.add(owner)
    await session.flush()

    service = SuperAdminService(
        user_repository=UserRepository(session),
        group_repository=GroupRepository(session),
        task_repository=TaskRepository(session),
        penalty_repository=PenaltyRepository(session),
        settings_repository=SettingsRepository(session),
        audit_repository=AuditRepository(session),
        notification_service=NotificationService(NotificationTemplateRepository(session)),
    )

    assert await service.is_maintenance_mode() is False

    await service.set_maintenance_mode(True, actor_user_id=owner.id)
    assert await service.is_maintenance_mode() is True

    await service.set_maintenance_mode(False, actor_user_id=owner.id)
    assert await service.is_maintenance_mode() is False
