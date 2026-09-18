"""
Integratsiya testi: 2 soatlik ovoz berish oynasi.

Rasm yuklangandan (`TaskCompletion.completed_at`) keyin guruhdoshlar
faqat 2 soat ichida ✅/❌ ovoz bera oladi. Bu vaqt o'tgach yangi ovoz
rad etiladi - scheduler shu vaqtgacha yig'ilgan ovozlar bo'yicha
avtomatik hal qiladi (`resolve_expired_completion_votes`, alohida sinaladi).
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


async def _setup_pending_vote(client, session) -> tuple[int, int]:
    """
    Admin + a'zoni ro'yxatdan o'tkazadi, Telegram chatga bog'langan
    guruh ochadi (shuning uchun rasm yuklangach DARHOL tasdiqlanmaydi -
    ovoz berish PENDING holatida boshlanadi), vazifa yaratadi va navbat
    boshidagi a'zo rasm yuklab bajaradi.

    Qaytaradi: `(completion_id, voter_telegram_id)` - `voter_telegram_id`
    bajarmagan (demak, ovoz bera oladigan) a'zoning telegram_id'si.
    """
    await client.post(
        "/api/v1/users/register",
        json={"telegram_id": 6101, "full_name": "Admin", "username": "admin_v"},
        headers=HEADERS,
    )
    await client.post(
        "/api/v1/users/register",
        json={"telegram_id": 6102, "full_name": "A'zo", "username": "member_v"},
        headers=HEADERS,
    )

    resp = await client.post(
        "/api/v1/groups/create",
        json={"telegram_id": 6101, "name": "Vote Window Group", "telegram_chat_id": -1006101},
        headers=HEADERS,
    )
    body = resp.json()["data"]
    group_id, invite_code = body["group_id"], body["invite_code"]

    await client.post(
        "/api/v1/groups/join",
        json={"telegram_id": 6102, "invite_code": invite_code},
        headers=HEADERS,
    )

    resp = await client.post(
        "/api/v1/tasks/",
        json={
            "telegram_id": 6101,
            "group_id": group_id,
            "name": "Ovoz oynasi testi vazifasi",
        },
        headers=HEADERS,
    )
    task_id = resp.json()["data"]["task_id"]

    # A'zolar TASODIFIY tartibda navbatga qo'yiladi - navbat boshidagi
    # haqiqiy a'zoni topib, ANA SHU nomidan bajaramiz.
    resp = await client.get(f"/api/v1/tasks/{task_id}/queue/preview", headers=HEADERS)
    front_full_name = resp.json()["data"][0]["full_name"]
    front_telegram_id = 6101 if front_full_name == "Admin" else 6102

    resp = await client.post(
        f"/api/v1/completion/{task_id}",
        data={"telegram_id": str(front_telegram_id)},
        files={"photo": ("photo.jpg", b"fake-image-bytes", "image/jpeg")},
        headers=HEADERS,
    )
    assert resp.json()["success"] is True
    assert resp.json()["data"]["awaiting_vote"] is True

    result = await session.execute(select(TaskCompletion).order_by(TaskCompletion.id.desc()))
    completion = result.scalars().first()
    assert completion is not None

    voter_telegram_id = 6102 if front_telegram_id == 6101 else 6101
    return completion.id, voter_telegram_id


async def test_vote_accepted_within_two_hour_window(client, session):
    completion_id, voter_telegram_id = await _setup_pending_vote(client, session)

    resp = await client.post(
        f"/api/v1/completion/{completion_id}/vote",
        json={"telegram_id": voter_telegram_id, "approve": True},
        headers=HEADERS,
    )
    body = resp.json()
    assert body["success"] is True
    # Yolg'iz voter - eligible_total=1, needed=1 - darhol tasdiqlanadi.
    assert body["data"]["resolution"] == "approved"


async def test_vote_rejected_after_two_hour_window(client, session):
    completion_id, voter_telegram_id = await _setup_pending_vote(client, session)

    completion = await session.get(TaskCompletion, completion_id)
    completion.completed_at = datetime.now(timezone.utc) - timedelta(hours=2, minutes=1)
    await session.flush()

    resp = await client.post(
        f"/api/v1/completion/{completion_id}/vote",
        json={"telegram_id": voter_telegram_id, "approve": True},
        headers=HEADERS,
    )
    body = resp.json()
    assert body["success"] is False
    assert "2 soat" in body["message"]


async def test_vote_accepted_at_one_hour_fifty_nine_minutes(session, client):
    """Chegara holati: 1 soat 59 daqiqada hali ovoz qabul qilinishi kerak."""
    completion_id, voter_telegram_id = await _setup_pending_vote(client, session)

    completion = await session.get(TaskCompletion, completion_id)
    completion.completed_at = datetime.now(timezone.utc) - timedelta(hours=1, minutes=59)
    await session.flush()

    resp = await client.post(
        f"/api/v1/completion/{completion_id}/vote",
        json={"telegram_id": voter_telegram_id, "approve": False},
        headers=HEADERS,
    )
    assert resp.json()["success"] is True
