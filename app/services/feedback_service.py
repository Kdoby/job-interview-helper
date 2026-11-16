from langchain_core.runnables import Runnable

from app.agents.callbacks import TokenUsageTracker
from app.agents.errors import ainvoke_or_raise
from app.agents.feedback.outputs import FeedbackResult
from app.agents.feedback.prompts import (
    HIGH_CONFIDENCE_GUIDE,
    LOW_CONFIDENCE_GUIDE,
    NORMAL_CONFIDENCE_GUIDE,
)
from app.core.exceptions import AnswerNotFoundError
from app.domain.answer import Answer
from app.repositories.answer_repository import AnswerRepository
from app.schemas.answer import AiFeedbackResponse


class FeedbackService:
    def __init__(self, repository: AnswerRepository, feedback_graph: Runnable):
        self.repository = repository
        self.feedback_graph = feedback_graph

    # 1. 답변 조회
    def find_answer(self, answer_id: int) -> Answer:
        answer = self.repository.find_by_id(answer_id)

        if answer is None:
            raise AnswerNotFoundError(answer_id)

        return answer

    # 자신감별 지시문 선택
    def select_confidence_guide(self, confidence: int) -> str:
        if confidence <= 2:
            return LOW_CONFIDENCE_GUIDE
        if confidence >= 4:
            return HIGH_CONFIDENCE_GUIDE
        return NORMAL_CONFIDENCE_GUIDE

    def build_chain_input(self, answer: Answer) -> dict:
        return {
            "confidence_guide": self.select_confidence_guide(answer.confidence),
            "question": answer.question,
            "answer": answer.answer,
            "confidence": answer.confidence,
        }

    # LLM 호출
    async def generate_feedback(self, answer_id: int) -> AiFeedbackResponse:
        answer = self.find_answer(answer_id)
        chain_input = self.build_chain_input(answer)

        tracker = TokenUsageTracker()
        # 그래프는 상태 dict를 반환함
        result = await ainvoke_or_raise(
            self.feedback_graph, chain_input, config={"callbacks": [tracker]}
        )
        tracker.print_usage("feedback")

        analysis = result["analysis"]
        # 답변에 피드백, 점수 저장
        answer.feedback = result["feedback"]
        answer.score = analysis.score
        self.repository.save(answer)

        # level 필드는 제외하고 타입 변환
        return AiFeedbackResponse.model_validate(
            {"feedback": result["feedback"], **analysis.model_dump(exclude={"level"})}
        )
