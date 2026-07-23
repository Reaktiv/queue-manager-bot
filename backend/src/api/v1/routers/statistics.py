"""
Presentation Layer: A'zo statistikasi (jarima, bajarish foizi).
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.auth_deps import Identity, ensure_actor_can_access_group, verify_bot_or_mini_app
from ....api.deps import get_group_service, get_penalty_service, get_session
from ....services.group_service import GroupService
from ....services.penalty_service import PenaltyService

router = APIRouter(
    prefix="/statistics", tags=["Statistics"], dependencies=[Depends(verify_bot_or_mini_app)]
)


class ApiResponse(BaseModel):
    success: bool
    data: object | None = None
    message: str | None = None


@router.get("/member/{member_id}", response_model=ApiResponse)
async def get_member_statistics(
    member_id: int,
    session: AsyncSession = Depends(get_session),
    service: PenaltyService = Depends(get_penalty_service),
    group_service: GroupService = Depends(get_group_service),
    identity: Identity = Depends(verify_bot_or_mini_app),
):
    member = await group_service.get_member_by_id(member_id)
    if member is None:
        return ApiResponse(success=False, message="A'zo topilmadi")
    await ensure_actor_can_access_group(identity, member.group_id, session)

    stats = await service.get_member_statistics(member_id)
    return ApiResponse(success=True, data=stats)
