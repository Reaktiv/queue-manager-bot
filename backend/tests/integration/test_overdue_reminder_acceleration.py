"""
Integratsiya testi: jarima o'rniga qo'shilgan "muddati o'tgan vazifa uchun
soatiga bir marta eslatish" rejimi (`scheduler/jobs.py`,
`AssignmentRepository.has_open_overdue_streak`).

Vazifaning o'zi 120 daqiqalik eslatma oralig'iga sozlangan - agar a'zo
hali hech qachon kechiktirmagan bo'lsa shu 120 daqiqa qo'llanishi, lekin
kamida bir kun kechiktirgan bo'lsa (OVERDUE tarixi bor) qat'iy 60
daqiqaga tezlashishi kerak.
"""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.src.api import deps
from backend.src.core.config import settings
from backend.src.infrastructure.models.task import Task, TaskAssignment, TaskStatus
from backend.src.main import app
from backend.src.repositories.assignment_repository import AssignmentRepository
from backend.src.utils.datetime_utils import get_local_today

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


class _MockSessionContext:
    def __init__(self, s):
        self.s = s

    async def __aenter__(self):
        return self.s

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


async def _setup_task(client, session, admin_telegram_id: int, group_name: str) -> tuple[int, int]:
    """Guruh + vazifa (120 daqiqalik, kun bo'yi eslatma oynasi) yaratadi.
    Qaytaradi: `(task_id, front_member_telegram_id)`."""
    await client.post(
        "/api/v1/users/register",
        json={"telegram_id": admin_telegram_id, "full_name": "Overdue Admin"},
        headers=HEADERS,
    )
    resp = await client.post(
        "/api/v1/groups/create",
        json={"telegram_id": admin_telegram_id, "name": group_name},
        headers=HEADERS,
    )
    group_id = resp.json()["data"]["group_id"]

    resp = await client.post(
        "/api/v1/tasks/",
        json={
            "telegram_id": admin_telegram_id,
            "group_id": group_id,
            "name": "Overdue Task",
            "reminder_interval_min_minutes": 120,
            "reminder_interval_max_minutes": 120,
            "reminder_start_hour": 0,
            "reminder_end_hour": 23,
        },
        headers=HEADERS,
    )
    task_id = resp.json()["data"]["task_id"]
    return task_id, admin_telegram_id


async def test_reminder_uses_configured_interval_without_overdue_history(
    client, session, monkeypatch
):
    import backend.src.scheduler.jobs as jobs_module
    from backend.src.scheduler.jobs import send_reminders

    monkeypatch.setattr(jobs_module, "async_session_factory", lambda: _MockSessionContext(session))

    task_id, admin_telegram_id = await _setup_task(client, session, 8101, "No Streak Group")

    task = await session.get(Task, task_id)
    now = datetime.now(timezone.utc)
    task.next_reminder_at = now - timedelta(minutes=1)
    await session.flush()

    await send_reminders()

    await session.refresh(task)
    delta_minutes = (task.next_reminder_at - now).total_seconds() / 60
    assert 110 <= delta_minutes <= 130, f"expected ~120 min, got {delta_minutes}"


async def test_reminder_accelerates_to_hourly_after_overdue_streak(client, session, monkeypatch):
    import backend.src.scheduler.jobs as jobs_module
    from backend.src.scheduler.jobs import send_reminders

    monkeypatch.setattr(jobs_module, "async_session_factory", lambda: _MockSessionContext(session))

    task_id, admin_telegram_id = await _setup_task(client, session, 8102, "Streak Group")

    task = await session.get(Task, task_id)
    group_timezone = "Asia/Tashkent"
    today = get_local_today(group_timezone)

    # Navbat boshidagi a'zoni topamiz - bugungi assignment shu a'zo uchun
    # `create_task_with_queue` orqali allaqachon yaratilgan.
    resp = await client.get(f"/api/v1/tasks/{task_id}/queue/preview", headers=HEADERS)
    front_member_id = resp.json()["data"][0]["member_id"]

    # "Kecha" allaqachon kechiktirilgan (OVERDUE) - shu belgi mavjudligi
    # bugungi eslatmalarni tezlashtirishi kerak.
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    session.add(
        TaskAssignment(
            task_id=task_id,
            member_id=front_member_id,
            assigned_date=yesterday,
            due_date=yesterday,
            status=TaskStatus.OVERDUE,
        )
    )
    await session.flush()

    now = datetime.now(timezone.utc)
    task.next_reminder_at = now - timedelta(minutes=1)
    await session.flush()

    await send_reminders()

    await session.refresh(task)
    delta_minutes = (task.next_reminder_at - now).total_seconds() / 60
    assert 50 <= delta_minutes <= 70, f"expected ~60 min (accelerated), got {delta_minutes}"
