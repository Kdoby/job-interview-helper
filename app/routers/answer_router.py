import threading
import time

from fastapi import APIRouter

from app.dependencies import AnswerServiceDep, FeedbackServiceDep
from app.schemas.answer import AnswerCreateRequest, AnswerResponse
from app.schemas.feedback import AiFeedbackResponse

router = APIRouter(prefix="/api/answers", tags=["답변"])


def log(handler: str, message: str) -> None:
    now = time.strftime("%H:%M:%S")
    thread = threading.current_thread().name
    print(f"{now} [{handler}] {message} (스레드: {thread})")


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


# ai - 피드백 받기, 비동기
@router.post("/{answer_id}/feedback", summary="답변에 대한 피드백 받기")
async def get_feedback(
    answer_id: int, service: FeedbackServiceDep
) -> AiFeedbackResponse:

    log("async", "요청 받음")
    response = await service.create_feedback(answer_id)
    log("async", "요청 보냄")

    return response
