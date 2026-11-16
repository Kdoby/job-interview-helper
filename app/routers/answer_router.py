from typing import AsyncIterable

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.core.thread_log import log
from app.dependencies import AnswerServiceDep, ExistingAnswerDep, FeedbackServiceDep
from app.schemas.answer import AiFeedbackResponse, AnswerCreateRequest, AnswerResponse

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


# ai - 피드백 받기, 비동기
@router.post("/{answer_id}/feedback", summary="답변에 대한 피드백 받기")
async def generate_feedback(
    answer_id: int, service: FeedbackServiceDep
) -> AiFeedbackResponse:

    log("async", "요청 받음")
    response = await service.generate_feedback(answer_id)
    log("async", "요청 보냄")

    return response


@router.post(
    "/{answer_id}/feedback/stream",
    response_class=EventSourceResponse,
    summary="피드백 스트리밍 (SSE)",
)
async def stream_feedback(
    answer: ExistingAnswerDep, service: FeedbackServiceDep
) -> AsyncIterable[ServerSentEvent]:

    log("stream", "요청 받음")
    async for event, data in service.stream_feedback(answer):
        yield ServerSentEvent(event=event, data=data)
    log("stream", "스트림 종료")
