"""
Integratsiya testi: haqiqiy FastAPI ilovasi orqali to'liq foydalanuvchi
oqimini sinaydi (ro'yxatdan o'tish -> guruh -> vazifa -> navbat).

`get_session` dependency test bazasiga ulanadigan session bilan almashtiriladi.
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


async def test_full_flow_register_group_task_complete(client):  # 1) Admin ro'yxatdan o'tadi
    resp = await client.post(
        "/api/v1/users/register",
        json={
            "telegram_id": 5001,
            "full_name": "Admin User",
            "username": "admin1",
            "language": "uz",
        },
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 2) Oddiy a'zo ro'yxatdan o'tadi
    resp = await client.post(
        "/api/v1/users/register",
        json={
            "telegram_id": 5002,
            "full_name": "Regular Member",
            "username": "member1",
            "language": "uz",
        },
        headers=HEADERS,
    )
    assert resp.status_code == 200

    # 3) Admin guruh yaratadi
    resp = await client.post(
        "/api/v1/groups/create",
        json={"telegram_id": 5001, "name": "Integration Test Home"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    group_id = body["data"]["group_id"]
    invite_code = body["data"]["invite_code"]

    # 4) A'zo taklif kodi bilan qo'shiladi
    resp = await client.post(
        "/api/v1/groups/join",
        json={"telegram_id": 5002, "invite_code": invite_code},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 5) Qayta qo'shilishga urinish rad etilishi kerak
    resp = await client.post(
        "/api/v1/groups/join",
        json={"telegram_id": 5002, "invite_code": invite_code},
        headers=HEADERS,
    )
    assert resp.json()["success"] is False

    # 6) Admin vazifa yaratadi
    resp = await client.post(
        "/api/v1/tasks/",
        json={
            "telegram_id": 5001,
            "group_id": group_id,
            "name": "Test Vazifa",
            "require_photo": False,
        },
        headers=HEADERS,
    )
    assert resp.status_code == 200
    task_body = resp.json()
    assert task_body["success"] is True
    task_id = task_body["data"]["task_id"]

    # 7) Navbatni ko'ramiz - admin boshda bo'lishi kerak (birinchi qo'shilgan)
    resp = await client.get(f"/api/v1/tasks/{task_id}/queue/preview", headers=HEADERS)
    entries = resp.json()["data"]
    assert len(entries) == 2
    assert entries[0]["is_locked"] is True

    # 8) Rasmsiz (require_photo=False) vazifani bajarish
    resp = await client.post(
        f"/api/v1/completion/{task_id}",
        data={"telegram_id": "5001"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 9) Navbat endi ikkinchi a'zoga o'tgan bo'lishi kerak
    resp = await client.get(f"/api/v1/tasks/{task_id}/queue/preview", headers=HEADERS)
    entries_after = resp.json()["data"]
    locked_after = [e for e in entries_after if e["is_locked"]]
    assert len(locked_after) == 1  # faqat bitta yozuv qulflangan


async def test_internal_secret_required(client):
    resp = await client.get("/api/v1/groups/1/members")  # header'siz
    assert resp.status_code == 401


async def test_admin_swap_queue_endpoint_uses_member_ids(client):
    """
    `/tasks/{task_id}/queue/swap` endpointi `member_id_a`/`member_id_b`
    (TaskQueueEntry.member_id qiymatlari, entry PK emas) qabul qilishini
    va real HTTP so'rov orqali navbatdagi o'rinlarni to'g'ri
    almashtirishini tekshiradi (avval bu endpoint uchun hech qanday
    integratsiya testi yo'q edi).
    """
    await client.post(
        "/api/v1/users/register",
        json={"telegram_id": 6001, "full_name": "Swap Admin"},
        headers=HEADERS,
    )
    await client.post(
        "/api/v1/users/register",
        json={"telegram_id": 6002, "full_name": "Swap Member"},
        headers=HEADERS,
    )

    resp = await client.post(
        "/api/v1/groups/create",
        json={"telegram_id": 6001, "name": "Swap Test Group"},
        headers=HEADERS,
    )
    group_data = resp.json()["data"]
    invite_code = group_data["invite_code"]

    await client.post(
        "/api/v1/groups/join",
        json={"telegram_id": 6002, "invite_code": invite_code},
        headers=HEADERS,
    )

    resp = await client.post(
        "/api/v1/tasks/",
        json={
            "telegram_id": 6001,
            "group_id": group_data["group_id"],
            "name": "Swap Test Task",
            "require_photo": False,
        },
        headers=HEADERS,
    )
    task_id = resp.json()["data"]["task_id"]

    resp = await client.get(f"/api/v1/tasks/{task_id}/queue/preview", headers=HEADERS)
    entries_before = resp.json()["data"]
    assert len(entries_before) == 2
    member_id_first = entries_before[0]["member_id"]
    member_id_second = entries_before[1]["member_id"]
    assert entries_before[0]["is_locked"] is True

    resp = await client.post(
        f"/api/v1/tasks/{task_id}/queue/swap",
        json={
            "telegram_id": 6001,
            "member_id_a": member_id_first,
            "member_id_b": member_id_second,
        },
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    resp = await client.get(f"/api/v1/tasks/{task_id}/queue/preview", headers=HEADERS)
    entries_after = resp.json()["data"]
    assert entries_after[0]["member_id"] == member_id_second
    assert entries_after[1]["member_id"] == member_id_first


async def test_admin_reorder_queue_endpoint_sets_full_order(client):
    """
    `/tasks/{task_id}/queue/reorder` - admin butun navbatni (barcha
    a'zolarni) bir martada, yangi tartibda qayta belgilashi mumkin
    (oldingi `/queue/swap` faqat 2 tasini almashtirar edi).
    """
    for telegram_id, name in [(6101, "Reorder Admin"), (6102, "Member B"), (6103, "Member C")]:
        await client.post(
            "/api/v1/users/register",
            json={"telegram_id": telegram_id, "full_name": name},
            headers=HEADERS,
        )

    resp = await client.post(
        "/api/v1/groups/create",
        json={"telegram_id": 6101, "name": "Reorder Test Group"},
        headers=HEADERS,
    )
    group_data = resp.json()["data"]
    invite_code = group_data["invite_code"]

    for telegram_id in (6102, 6103):
        await client.post(
            "/api/v1/groups/join",
            json={"telegram_id": telegram_id, "invite_code": invite_code},
            headers=HEADERS,
        )

    resp = await client.post(
        "/api/v1/tasks/",
        json={
            "telegram_id": 6101,
            "group_id": group_data["group_id"],
            "name": "Reorder Test Task",
            "require_photo": False,
        },
        headers=HEADERS,
    )
    task_id = resp.json()["data"]["task_id"]

    resp = await client.get(f"/api/v1/tasks/{task_id}/queue/full", headers=HEADERS)
    entries_before = resp.json()["data"]
    assert len(entries_before) == 3
    member_ids = [e["member_id"] for e in entries_before]
    new_order = list(reversed(member_ids))

    resp = await client.post(
        f"/api/v1/tasks/{task_id}/queue/reorder",
        json={"telegram_id": 6101, "member_ids": new_order},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    resp = await client.get(f"/api/v1/tasks/{task_id}/queue/full", headers=HEADERS)
    entries_after = resp.json()["data"]
    assert [e["member_id"] for e in entries_after] == new_order
    assert entries_after[0]["is_locked"] is True


async def test_admin_reorder_queue_endpoint_rejects_incomplete_list(client):
    await client.post(
        "/api/v1/users/register",
        json={"telegram_id": 6201, "full_name": "Reorder Admin 2"},
        headers=HEADERS,
    )
    await client.post(
        "/api/v1/users/register",
        json={"telegram_id": 6202, "full_name": "Reorder Member 2"},
        headers=HEADERS,
    )

    resp = await client.post(
        "/api/v1/groups/create",
        json={"telegram_id": 6201, "name": "Reorder Test Group 2"},
        headers=HEADERS,
    )
    group_data = resp.json()["data"]
    await client.post(
        "/api/v1/groups/join",
        json={"telegram_id": 6202, "invite_code": group_data["invite_code"]},
        headers=HEADERS,
    )

    resp = await client.post(
        "/api/v1/tasks/",
        json={
            "telegram_id": 6201,
            "group_id": group_data["group_id"],
            "name": "Reorder Test Task 2",
            "require_photo": False,
        },
        headers=HEADERS,
    )
    task_id = resp.json()["data"]["task_id"]

    resp = await client.get(f"/api/v1/tasks/{task_id}/queue/full", headers=HEADERS)
    member_ids = [e["member_id"] for e in resp.json()["data"]]

    resp = await client.post(
        f"/api/v1/tasks/{task_id}/queue/reorder",
        json={"telegram_id": 6201, "member_ids": member_ids[:1]},
        headers=HEADERS,
    )
    assert resp.json()["success"] is False


async def test_set_and_get_phone_number(client):
    """
    Bot foydalanuvchi "kontakt ulashish" tugmasi orqali o'z raqamini
    yuborganda `/users/phone` shu raqamni saqlaydi va keyingi
    `GET /users/{telegram_id}` javobida qaytarilishi kerak.
    """
    await client.post(
        "/api/v1/users/register",
        json={"telegram_id": 7001, "full_name": "Phone User"},
        headers=HEADERS,
    )

    resp = await client.get("/api/v1/users/7001", headers=HEADERS)
    assert resp.json()["data"]["phone_number"] is None

    resp = await client.post(
        "/api/v1/users/phone",
        json={"telegram_id": 7001, "phone_number": "+998901234567"},
        headers=HEADERS,
    )
    assert resp.json()["success"] is True
    assert resp.json()["data"]["phone_number"] == "+998901234567"

    resp = await client.get("/api/v1/users/7001", headers=HEADERS)
    assert resp.json()["data"]["phone_number"] == "+998901234567"


async def test_invalid_invite_code_returns_failure(client):
    await client.post(
        "/api/v1/users/register",
        json={"telegram_id": 5010, "full_name": "Solo User"},
        headers=HEADERS,
    )
    resp = await client.post(
        "/api/v1/groups/join",
        json={"telegram_id": 5010, "invite_code": "NONEXISTENT"},
        headers=HEADERS,
    )
    assert resp.json()["success"] is False


async def test_group_admin_broadcast(client):
    # 1) Admin ro'yxatdan o'tadi
    await client.post(
        "/api/v1/users/register",
        json={
            "telegram_id": 6001,
            "full_name": "Admin User",
            "username": "admin_broad",
            "language": "uz",
        },
        headers=HEADERS,
    )
    # 2) Guruh yaratadi
    r2 = await client.post(
        "/api/v1/groups/create",
        json={"telegram_id": 6001, "name": "Broadcast Test Group"},
        headers=HEADERS,
    )
    group_id = r2.json()["data"]["group_id"]

    # 3) Broadcast yuborishga harakat qiladi
    resp_broad = await client.post(
        f"/api/v1/groups/{group_id}/broadcast",
        json={"telegram_id": 6001, "message": "Ommaviy e'lon matni!"},
        headers=HEADERS,
    )
    assert resp_broad.status_code == 200
    assert resp_broad.json()["success"] is True


async def test_link_group_by_code(client):
    # 1) Admin ro'yxatdan o'tadi
    await client.post(
        "/api/v1/users/register",
        json={
            "telegram_id": 7001,
            "full_name": "Admin Linker",
            "username": "admin_linker",
            "language": "uz",
        },
        headers=HEADERS,
    )
    # 2) Guruh yaratadi
    r = await client.post(
        "/api/v1/groups/create",
        json={"telegram_id": 7001, "name": "Linkable Group"},
        headers=HEADERS,
    )
    data = r.json()["data"]
    invite_code = data["invite_code"]

    # 3) Bog'lashga harakat qiladi
    resp_link = await client.post(
        "/api/v1/groups/link-by-code",
        json={
            "telegram_id": 7001,
            "invite_code": invite_code,
            "telegram_chat_id": -999888777,
        },
        headers=HEADERS,
    )
    assert resp_link.status_code == 200
    assert resp_link.json()["success"] is True
    assert resp_link.json()["data"]["group_name"] == "Linkable Group"


async def test_send_pre_warnings(client, session, monkeypatch):
    from datetime import datetime, timezone, timedelta
    from zoneinfo import ZoneInfo
    from backend.src.infrastructure.models.task import Task
    from backend.src.scheduler.jobs import send_pre_warnings

    # Monkeypatch async_session_factory in jobs module to share the same session transaction
    import backend.src.scheduler.jobs as jobs_module

    class MockSessionContext:
        def __init__(self, s):
            self.s = s
        async def __aenter__(self):
            return self.s
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(jobs_module, "async_session_factory", lambda: MockSessionContext(session))

    # 1) Admin ro'yxatdan o'tadi
    await client.post(
        "/api/v1/users/register",
        json={"telegram_id": 8001, "full_name": "Admin Warner", "username": "admin_warner", "language": "uz"},
        headers=HEADERS,
    )
    # 2) Guruh yaratadi
    r = await client.post(
        "/api/v1/groups/create",
        json={"telegram_id": 8001, "name": "Warning Group"},
        headers=HEADERS,
    )
    group_id = r.json()["data"]["group_id"]

    # 3) Task yaratadi
    tz = ZoneInfo("Asia/Tashkent")
    local_now = datetime.now(tz)
    tomorrow = local_now + timedelta(days=1)

    resp_task = await client.post(
        "/api/v1/tasks/",
        json={
            "telegram_id": 8001,
            "group_id": group_id,
            "name": "Warning Task",
            "schedule_type": "every_x_days",
            "schedule_interval_days": 3,
            "start_date": datetime.now(timezone.utc).date().isoformat(),
            "reminder_start_hour": 0,
        },
        headers=HEADERS,
    )
    assert resp_task.status_code == 200
    task_id = resp_task.json()["data"]["task_id"]

    # Update next_execution_date in database directly
    task_db = await session.get(Task, task_id)
    task_db.next_execution_date = tomorrow
    await session.flush()

    # 4) Run the job
    await send_pre_warnings()

    # 5) Verify database state
    await session.refresh(task_db)
    assert task_db.last_pre_warning_sent_date is not None
    assert task_db.last_pre_warning_sent_date.astimezone(tz).date() == tomorrow.date()
