from typing import Annotated

from fastapi import Depends, Request

from app.ai.components import AiComponents
from app.repositories.answer_repository import AnswerRepository
from app.services.answer_service import AnswerService
from app.services.feedback_service import FeedbackService
from app.services.question_service import QuestionService

# def get_llm_client(request: Request) -> LlmClient:
#     return request.app.state.llm_client


# LlmClientDep = Annotated[LlmClient, Depends(get_llm_client)]


def get_ai(request: Request) -> AiComponents:
    return request.app.state.ai


AiDep = Annotated[AiComponents, Depends(get_ai)]

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


# 각 서비스에는 필요한 체인 하나만 넘김


def get_feedback_service(
    repository: AnswerRepositoryDep,
    ai: AiDep,
) -> FeedbackService:
    return FeedbackService(repository, ai.feedback_chain)


FeedbackServiceDep = Annotated[FeedbackService, Depends(get_feedback_service)]


def get_question_service(
    ai: AiDep,
) -> QuestionService:
    return QuestionService(ai.question_chain)


QuestionServiceDep = Annotated[QuestionService, Depends(get_question_service)]
