from fastapi import APIRouter

from app.dependencies import AnswerServiceDep
from app.schemas.answer import AnswerCreateRequest, AnswerResponse


router = APIRouter(prefix="/api/answers", tags=["답변"])


@router.get("", summary="전체 답변 목록 조회")
def find_answers(service: AnswerServiceDep) -> list[AnswerResponse]:
    return service.find_answers()


@router.get("/{answer_id}", summary="답변 하나 조회")
def find_answer(answer_id: int, service: AnswerServiceDep) -> AnswerResponse:
    return service.find_answer(answer_id)


@router.post("", status_code=201, summary="답변 등록")
def register_answer(
    request: AnswerCreateRequest, service: AnswerServiceDep
) -> AnswerResponse:
    return service.register_answer(request)
