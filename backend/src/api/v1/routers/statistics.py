"""
Presentation Layer: A'zo statistikasi (jarima, bajarish foizi).
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ....api.deps import get_penalty_service
from ....services.penalty_service import PenaltyService

router = APIRouter(prefix="/statistics", tags=["Statistics"])


class ApiResponse(BaseModel):
    success: bool
    data: object | None = None
    message: str | None = None


@router.get("/member/{member_id}", response_model=ApiResponse)
async def get_member_statistics(
    member_id: int, service: PenaltyService = Depends(get_penalty_service)
):
    stats = await service.get_member_statistics(member_id)
    return ApiResponse(success=True, data=stats)
