from app.core.exceptions import AnswerNotFoundError
from app.domain.answer import Answer
from app.repositories.answer_repository import AnswerRepository
from app.schemas.answer import AnswerCreateRequest, AnswerResponse


class AnswerService:
    def __init__(self, repository: AnswerRepository):
        self.repository = repository

    def find_answers(self) -> list[AnswerResponse]:
        answers = self.repository.find_all()

        return [AnswerResponse.from_answer(answer) for answer in answers]

    # 답변 찾기
    def find_answer(self, answer_id: int) -> AnswerResponse | None:
        answer = self.repository.find_by_id(answer_id)

        if answer is None:
            raise AnswerNotFoundError(answer_id)

        return AnswerResponse.from_answer(answer)

    # 답변 기록 등록
    def register_answer(self, request: AnswerCreateRequest) -> AnswerResponse:
        answer = Answer(
            answer_id=0,
            user_name=request.user_name,
            question=request.question,
            answer=request.answer,
            confidence=request.confidence,
        )

        saved = self.repository.save(answer)

        return AnswerResponse.from_answer(saved)
