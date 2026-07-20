"""
Presentation Layer: Export (CSV/Excel) va oddiy qidiruv endpointlari.
"""

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.auth_deps import verify_bot_or_mini_app
from ....api.deps import get_session
from ....infrastructure.models.group import Member
from ....infrastructure.models.task import Task, TaskAssignment, TaskCompletion
from ....infrastructure.models.user import User

router = APIRouter(
    prefix="/export", tags=["Export & Search"], dependencies=[Depends(verify_bot_or_mini_app)]
)


class ApiResponse(BaseModel):
    success: bool
    data: object | None = None
    message: str | None = None


@router.get("/group/{group_id}/history.csv")
async def export_history_csv(group_id: int, session: AsyncSession = Depends(get_session)):
    """Guruhning butun bajarish tarixini CSV formatida eksport qiladi."""
    stmt = (
        select(TaskCompletion, TaskAssignment, Task, User)
        .join(TaskAssignment, TaskCompletion.assignment_id == TaskAssignment.id)
        .join(Task, TaskAssignment.task_id == Task.id)
        .join(Member, TaskCompletion.member_id == Member.id)
        .join(User, Member.user_id == User.id)
        .where(Task.group_id == group_id)
        .order_by(TaskCompletion.completed_at.desc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Vazifa", "Bajaruvchi", "Bajarilgan vaqt", "Izoh", "Rasm yo'li"])
    for completion, assignment, task, user in rows:
        writer.writerow(
            [
                task.name,
                user.full_name,
                completion.completed_at.isoformat(),
                completion.caption or "",
                completion.photo_path or "",
            ]
        )
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=group_{group_id}_history.csv"},
    )


@router.get("/group/{group_id}/history.xlsx")
async def export_history_xlsx(group_id: int, session: AsyncSession = Depends(get_session)):
    """Guruhning bajarish tarixini Excel (.xlsx) formatida eksport qiladi."""
    from openpyxl import Workbook

    stmt = (
        select(TaskCompletion, TaskAssignment, Task, User)
        .join(TaskAssignment, TaskCompletion.assignment_id == TaskAssignment.id)
        .join(Task, TaskAssignment.task_id == Task.id)
        .join(Member, TaskCompletion.member_id == Member.id)
        .join(User, Member.user_id == User.id)
        .where(Task.group_id == group_id)
        .order_by(TaskCompletion.completed_at.desc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Tarix"
    sheet.append(["Vazifa", "Bajaruvchi", "Bajarilgan vaqt", "Izoh", "Rasm yo'li"])
    for completion, assignment, task, user in rows:
        sheet.append(
            [
                task.name,
                user.full_name,
                completion.completed_at.isoformat(),
                completion.caption or "",
                completion.photo_path or "",
            ]
        )

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=group_{group_id}_history.xlsx"},
    )


@router.get("/search", response_model=ApiResponse)
async def global_search(query: str, group_id: int, session: AsyncSession = Depends(get_session)):
    """
    Guruh doirasida vazifa nomi va a'zo ismi bo'yicha oddiy qidiruv
    (spec'dagi "Global Search" ning soddalashtirilgan MVP versiyasi).
    """
    like_pattern = f"%{query}%"

    task_stmt = select(Task).where(Task.group_id == group_id, Task.name.ilike(like_pattern))
    task_result = await session.execute(task_stmt)
    tasks = [{"type": "task", "id": t.id, "name": t.name} for t in task_result.scalars().all()]

    member_stmt = (
        select(Member, User)
        .join(User, Member.user_id == User.id)
        .where(Member.group_id == group_id, User.full_name.ilike(like_pattern))
    )
    member_result = await session.execute(member_stmt)
    members = [{"type": "member", "id": m.id, "name": u.full_name} for m, u in member_result.all()]

    return ApiResponse(success=True, data={"tasks": tasks, "members": members})
