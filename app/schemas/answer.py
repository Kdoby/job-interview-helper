from pydantic import Field

from app.domain.answer import Answer
from app.schemas.base import CamelModel


class AnswerCreateRequest(CamelModel):
    user_name: str = Field(min_length=1, max_length=10)
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1, max_length=300)
    confidence: int = Field(ge=1, le=10)


class AnswerResponse(CamelModel):
    answer_id: int
    user_name: str
    question: str
    answer: str
    confidence: int

    @classmethod
    def from_answer(cls, answer: Answer) -> AnswerResponse:
        return cls(
            answer_id=answer.answer_id,
            user_name=answer.user_name,
            question=answer.question,
            answer=answer.answer,
            confidence=answer.confidence,
        )
