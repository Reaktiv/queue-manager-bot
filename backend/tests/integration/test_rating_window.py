"""
Integratsiya testi: 1 soatlik baholash oynasi.

Topshiriq tasdiqlangandan (`resolved_at`) keyin guruhdoshlar faqat 1 soat
ichida 1-5 yulduz bilan baho bera oladi. Bu vaqt o'tgach yangi baho rad
etiladi - o'sha paytgacha yig'ilgan o'rtacha (yoki hech kim bermagan bo'lsa
5.0 baza) yakuniy hisoblanadi.
"""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.src.api import deps
from backend.src.core.config import settings
from backend.src.infrastructure.models.task import TaskCompletion
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


async def _setup_completed_task(client, session) -> tuple[int, int]:
    """
    Admin + a'zoni ro'yxatdan o'tkazadi, guruh ochadi, vazifa yaratadi va
    navbat boshidagi a'zo uni bajaradi. Guruhning `telegram_chat_id`
    yo'qligi sababli darhol AVTOMATIK tasdiqlanadi (guruh ovoz berish
    shart emas) - bu baholash oynasini sinash uchun eng qisqa yo'l.

    Qaytaradi: `(completion_id, rater_telegram_id)` - `rater_telegram_id`
    bajarmagan (demak, baho bera oladigan) a'zoning telegram_id'si.
    """
    await client.post(
        "/api/v1/users/register",
        json={"telegram_id": 6001, "full_name": "Admin", "username": "admin_r"},
        headers=HEADERS,
    )
    await client.post(
        "/api/v1/users/register",
        json={"telegram_id": 6002, "full_name": "A'zo", "username": "member_r"},
        headers=HEADERS,
    )

    resp = await client.post(
        "/api/v1/groups/create",
        json={"telegram_id": 6001, "name": "Rating Window Group"},
        headers=HEADERS,
    )
    body = resp.json()["data"]
    group_id, invite_code = body["group_id"], body["invite_code"]

    await client.post(
        "/api/v1/groups/join",
        json={"telegram_id": 6002, "invite_code": invite_code},
        headers=HEADERS,
    )

    resp = await client.post(
        "/api/v1/tasks/",
        json={
            "telegram_id": 6001,
            "group_id": group_id,
            "name": "Oyna testi vazifasi",
            "require_photo": False,
        },
        headers=HEADERS,
    )
    task_id = resp.json()["data"]["task_id"]

    # DIQQAT: a'zolar endi TASODIFIY tartibda navbatga qo'yiladi (adolatli
    # boshlanish uchun) - "admin doim boshda" deb taxmin qilib bo'lmaydi.
    # Navbat boshidagi haqiqiy a'zoni topib, ANA SHU nomidan bajaramiz.
    resp = await client.get(f"/api/v1/tasks/{task_id}/queue/preview", headers=HEADERS)
    front_full_name = resp.json()["data"][0]["full_name"]
    front_telegram_id = 6001 if front_full_name == "Admin" else 6002

    resp = await client.post(
        f"/api/v1/completion/{task_id}",
        data={"telegram_id": str(front_telegram_id)},
        headers=HEADERS,
    )
    assert resp.json()["success"] is True
    assert resp.json()["data"]["auto_approved"] is True

    result = await session.execute(select(TaskCompletion).order_by(TaskCompletion.id.desc()))
    completion = result.scalars().first()
    assert completion is not None

    rater_telegram_id = 6002 if front_telegram_id == 6001 else 6001
    return completion.id, rater_telegram_id


async def test_rating_accepted_within_one_hour_window(client, session):
    completion_id, rater_telegram_id = await _setup_completed_task(client, session)

    resp = await client.post(
        f"/api/v1/completion/{completion_id}/rate",
        json={"telegram_id": rater_telegram_id, "stars": 5},
        headers=HEADERS,
    )
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["member_rating_stars"] == 5.0


async def test_rating_rejected_after_one_hour_window(client, session):
    completion_id, rater_telegram_id = await _setup_completed_task(client, session)

    completion = await session.get(TaskCompletion, completion_id)
    completion.resolved_at = datetime.now(timezone.utc) - timedelta(hours=1, minutes=1)
    await session.flush()

    resp = await client.post(
        f"/api/v1/completion/{completion_id}/rate",
        json={"telegram_id": rater_telegram_id, "stars": 5},
        headers=HEADERS,
    )
    body = resp.json()
    assert body["success"] is False
    assert "1 soat" in body["message"]


async def test_rating_accepted_at_fifty_nine_minutes(session, client):
    """Chegara holati: 59 daqiqada hali baho qabul qilinishi kerak."""
    completion_id, rater_telegram_id = await _setup_completed_task(client, session)

    completion = await session.get(TaskCompletion, completion_id)
    completion.resolved_at = datetime.now(timezone.utc) - timedelta(minutes=59)
    await session.flush()

    resp = await client.post(
        f"/api/v1/completion/{completion_id}/rate",
        json={"telegram_id": rater_telegram_id, "stars": 4},
        headers=HEADERS,
    )
    assert resp.json()["success"] is True
