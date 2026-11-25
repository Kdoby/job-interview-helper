from fastapi import APIRouter

from app.api.dependencies import InterviewServiceDep
from app.schemas.interview import (
    InterviewAnswerRequest,
    InterviewCreateRequest,
    InterviewSessionResponse,
    InterviewTurnResponse,
)

router = APIRouter(prefix="/api/interviews", tags=["인터뷰"])


@router.post("", status_code=201, summary="인터뷰 시작 요청")
async def create_interview(
    request: InterviewCreateRequest, service: InterviewServiceDep
) -> InterviewTurnResponse:
    return await service.start(request)


@router.post("/{session_id}/answers", summary="인터뷰 답변 제출")
async def create_interview_answer(
    session_id: str, request: InterviewAnswerRequest, service: InterviewServiceDep
) -> InterviewTurnResponse:
    return await service.answer(session_id, request)


@router.get("/{session_id}", summary="인터뷰 문답 기록 조회")
async def get_interview_record(
    session_id: str, service: InterviewServiceDep
) -> InterviewSessionResponse:
    return await service.get(session_id)
