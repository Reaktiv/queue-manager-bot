"""
Integratsiya testi: vazifani PATCH orqali to'liq tahrirlash
(`/api/v1/tasks/{task_id}`) - Mini App'dagi "Tahrirlash" formasi shu
endpointni chaqiradi.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.src.api import deps
from backend.src.core.config import settings
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


async def _setup_task(client) -> tuple[int, int, int, str]:
    """Admin ro'yxatdan o'tadi, guruh ochadi, vazifa yaratadi.
    Qaytaradi: `(admin_telegram_id, group_id, task_id, invite_code)`."""
    admin_telegram_id = 7201
    await client.post(
        "/api/v1/users/register",
        json={"telegram_id": admin_telegram_id, "full_name": "Task Editor"},
        headers=HEADERS,
    )
    resp = await client.post(
        "/api/v1/groups/create",
        json={"telegram_id": admin_telegram_id, "name": "Edit Task Group"},
        headers=HEADERS,
    )
    group_data = resp.json()["data"]
    group_id = group_data["group_id"]
    invite_code = group_data["invite_code"]

    resp = await client.post(
        "/api/v1/tasks/",
        json={
            "telegram_id": admin_telegram_id,
            "group_id": group_id,
            "name": "Original nom",
            "schedule_interval_days": 1,
            "start_date": "2026-01-01",
        },
        headers=HEADERS,
    )
    task_id = resp.json()["data"]["task_id"]
    return admin_telegram_id, group_id, task_id, invite_code


async def test_update_task_changes_all_editable_fields(client):
    admin_telegram_id, group_id, task_id, _invite_code = await _setup_task(client)

    resp = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={
            "telegram_id": admin_telegram_id,
            "name": "Yangi nom",
            "description": "Yangi tavsif",
            "schedule_interval_days": 3,
            "next_execution_date": "2026-02-20",
            "require_photo": False,
            "reminder_interval_min_minutes": 30,
            "reminder_interval_max_minutes": 90,
            "reminder_start_hour": 9,
            "reminder_end_hour": 21,
            "is_active": False,
        },
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    resp = await client.get(
        f"/api/v1/tasks/group/{group_id}?include_inactive=true", headers=HEADERS
    )
    task = next(t for t in resp.json()["data"] if t["id"] == task_id)

    assert task["name"] == "Yangi nom"
    assert task["description"] == "Yangi tavsif"
    assert task["schedule_interval_days"] == 3
    assert task["next_cycle_date"] == "2026-02-20"
    assert task["require_photo"] is False
    assert task["reminder_interval_min_minutes"] == 30
    assert task["reminder_interval_max_minutes"] == 90
    assert task["reminder_start_hour"] == 9
    assert task["reminder_end_hour"] == 21
    assert task["is_active"] is False

    # `include_inactive` bermasa - bot buyruqlari kutgani kabi, o'chirilgan
    # vazifa ro'yxatdan yashirinadi.
    resp = await client.get(f"/api/v1/tasks/group/{group_id}", headers=HEADERS)
    assert all(t["id"] != task_id for t in resp.json()["data"])


async def test_update_task_rejects_invalid_date_format(client):
    admin_telegram_id, _group_id, task_id, _invite_code = await _setup_task(client)

    resp = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"telegram_id": admin_telegram_id, "next_execution_date": "20-02-2026"},
        headers=HEADERS,
    )
    body = resp.json()
    assert body["success"] is False
    assert "Sana formati" in body["message"]


async def test_update_task_requires_admin(client):
    _admin_telegram_id, _group_id, task_id, invite_code = await _setup_task(client)

    member_telegram_id = 7202
    await client.post(
        "/api/v1/users/register",
        json={"telegram_id": member_telegram_id, "full_name": "Regular Member"},
        headers=HEADERS,
    )
    await client.post(
        "/api/v1/groups/join",
        json={"telegram_id": member_telegram_id, "invite_code": invite_code},
        headers=HEADERS,
    )

    resp = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"telegram_id": member_telegram_id, "name": "Ruxsatsiz o'zgartirish"},
        headers=HEADERS,
    )
    assert resp.status_code == 403
