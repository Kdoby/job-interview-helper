from fastapi import APIRouter

from app.core.thread_log import log
from app.dependencies import QuestionServiceDep
from app.schemas.question import AiQuestionResponse


router = APIRouter(prefix="/api/questions", tags=["면접 질문"])


# 1. 질문 생성 - 동기
@router.post("", summary="면접 질문 생성")
def generate_job_question(service: QuestionServiceDep) -> AiQuestionResponse:
    log("sync", "요청 받음")
    response = service.generate_question()
    log("sync", "요청 보냄")

    return response
