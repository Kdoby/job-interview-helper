from typing import Annotated

from fastapi import Depends, Request

from app.agents.components import AiComponents
from app.core.config import get_settings
from app.domain.answer import Answer
from app.repositories.answer_repository import AnswerRepository
from app.services.answer_service import AnswerService
from app.services.feedback_service import FeedbackService
from app.services.interview_service import InterviewService
from app.services.question_service import QuestionService
from app.services.coaching_service import CoachingService


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
    return FeedbackService(repository, ai.feedback_graph, ai.feedback_stream_graph)


FeedbackServiceDep = Annotated[FeedbackService, Depends(get_feedback_service)]


# 스트림은 응답 헤더(200)를 먼저 보내므로, 404 검사는 응답 전에 풀리는 의존성에서 해야함
def get_existing_answer(answer_id: int, service: FeedbackServiceDep) -> Answer:
    return service.find_answer(answer_id)


ExistingAnswerDep = Annotated[Answer, Depends(get_existing_answer)]


def get_question_service(
    ai: AiDep,
) -> QuestionService:
    return QuestionService(ai.question_graph)


QuestionServiceDep = Annotated[QuestionService, Depends(get_question_service)]


def get_coaching_service(repository: AnswerRepositoryDep, ai: AiDep) -> CoachingService:
    settings = get_settings()
    return CoachingService(
        repository,
        ai.coaching_graph,
        settings.retry_target_score,
        settings.retry_max_attempts,
    )


CoachingServiceDep = Annotated[CoachingService, Depends(get_coaching_service)]


def get_interview_service(ai: AiDep) -> InterviewService:
    return InterviewService(ai.interview_graph)


InterviewServiceDep = Annotated[InterviewService, Depends(get_interview_service)]
