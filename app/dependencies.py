from typing import Annotated

from fastapi import Depends

from app.repositories.answer_repository import AnswerRepository
from app.services.answer_service import AnswerService

# 서버가 실행될 때 한 번만 만들어짐(싱글턴)
answer_repository = AnswerRepository()


# AnswerRepository를 꺼내주는 의존성 함수
def get_answer_repository() -> AnswerRepository:
    return answer_repository


# AnswerService 객체를 만들어주는 의존성 함수
def get_answer_service(
    repository: Annotated[AnswerRepository, Depends(get_answer_repository)],
) -> AnswerService:
    return AnswerService(repository)


# 핸들러마다 반복해서 적지 않도록 해줌
AnswerServiceDep = Annotated[AnswerService, Depends(get_answer_service)]
