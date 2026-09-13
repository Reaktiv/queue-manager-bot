import pytest

from backend.src.repositories.group_repository import GroupRepository
from backend.src.repositories.task_repository import TaskRepository
from backend.src.repositories.queue_repository import QueueRepository
from backend.src.repositories.user_repository import UserRepository
from backend.src.services.group_service import DuplicateGroupChatIdError, GroupService


@pytest.mark.asyncio
async def test_duplicate_telegram_chat_id_returns_domain_error_not_500(session):
    user_repo = UserRepository(session)
    u1 = await user_repo.create(telegram_id=1001, full_name="User One", username=None, language="uz")
    u2 = await user_repo.create(telegram_id=1002, full_name="User Two", username=None, language="uz")

    group_repo = GroupRepository(session)
    service = GroupService(group_repo, TaskRepository(session), QueueRepository(session))

    group1 = await service.create_group(
        name="Group 1", created_by_user_id=u1.id, telegram_chat_id=999999
    )
    await session.commit()
    assert group1.telegram_chat_id == 999999

    with pytest.raises(DuplicateGroupChatIdError):
        await service.create_group(
            name="Group 2", created_by_user_id=u2.id, telegram_chat_id=999999
        )
