from typing import Annotated

from fastapi import Depends, Request

from app.clients.llm_client import LlmClient
from app.repositories.answer_repository import AnswerRepository
from app.services.answer_service import AnswerService
from app.services.feedback_service import FeedbackService

# 서버가 실행될 때 한 번만 만들어짐(싱글턴)
answer_repository = AnswerRepository()


# AnswerRepository를 꺼내주는 의존성 함수
def get_answer_repository() -> AnswerRepository:
    return answer_repository


# 핸들러마다 반복해서 적지 않도록 해줌
AnswerRepositoryDep = Annotated[AnswerRepository, Depends(get_answer_repository)]


# AnswerService 객체를 만들어주는 의존성 함수
def get_answer_service(
    repository: AnswerRepositoryDep,
) -> AnswerService:
    return AnswerService(repository)


AnswerServiceDep = Annotated[AnswerService, Depends(get_answer_service)]


def get_llm_client(request: Request) -> LlmClient:
    return request.app.state.llm_client


LlmClientDep = Annotated[LlmClient, Depends(get_llm_client)]


def get_feedback_service(
    repository: AnswerRepositoryDep,
    llm_client: LlmClientDep,
) -> FeedbackService:
    return FeedbackService(repository, llm_client)


FeedbackServiceDep = Annotated[FeedbackService, Depends(get_feedback_service)]
