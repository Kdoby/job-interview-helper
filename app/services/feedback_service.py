from typing import AsyncIterator

from langchain_core.runnables import Runnable

from app.agents.callbacks import TokenUsageTracker
from app.agents.errors import ainvoke_or_raise, astream_or_raise
from app.agents.feedback.outputs import FeedbackAnalysis
from app.agents.feedback.prompts import (
    HIGH_CONFIDENCE_GUIDE,
    LOW_CONFIDENCE_GUIDE,
    NORMAL_CONFIDENCE_GUIDE,
)
from app.core.exceptions import AiRequestError, AnswerNotFoundError
from app.domain.answer import Answer
from app.repositories.answer_repository import AnswerRepository
from app.schemas.answer import AiFeedbackResponse


class FeedbackService:
    def __init__(
        self,
        repository: AnswerRepository,
        feedback_graph: Runnable,
        feedback_stream_graph: Runnable,
    ):
        self.repository = repository
        self.feedback_graph = feedback_graph
        self.feedback_stream_graph = feedback_stream_graph

    # 1. 답변 조회
    def find_answer(self, answer_id: int) -> Answer:
        answer = self.repository.find_by_id(answer_id)

        if answer is None:
            raise AnswerNotFoundError(answer_id)

        return answer

    def save_feedback(
        self, answer: Answer, feedback: str, analysis: FeedbackAnalysis
    ) -> AiFeedbackResponse:
        answer.feedback = feedback
        answer.score = analysis.score
        answer.missing_concepts = analysis.missing_concepts

        self.repository.save(answer)

        return AiFeedbackResponse.model_validate(
            {"feedback": feedback, **analysis.model_dump(exclude={"level"})}
        )

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

        return self.save_feedback(answer, result["feedback"], result["analysis"])

    async def stream_feedback(self, answer: Answer) -> AsyncIterator[tuple[str, dict]]:
        chain_input = self.build_chain_input(answer)
        tracker = TokenUsageTracker()

        feedback = ""
        analysis = None

        try:
            async for mode, payload in astream_or_raise(
                self.feedback_stream_graph,
                chain_input,
                {"callbacks": [tracker]},
                # 이 두 종류의 소식을 받겠다
                stream_mode=["messages", "updates"],
            ):
                # token 하나씩 스트리밍
                if mode == "messages":
                    chunk, metadata = payload
                    if metadata.get("langgraph_node") == "generate" and chunk.text:
                        yield "token", {"text": str(chunk.text)}

                # 노드가 끝날 때 한 번씩: {"노드이름": 그 노드가 반환한 dict}
                elif mode == "updates":
                    if "generate" in payload:
                        feedback = payload["generate"]["feedback"]
                    if "analyze" in payload:
                        analysis = payload["analyze"]["analysis"]

            response = self.save_feedback(answer, feedback, analysis)
            # 전체 구조화된 출력
            yield "result", response.model_dump(by_alias=True)

        except AiRequestError as e:
            # 응답 코드는 이미 200이므로 error 이벤트로 알리고 끝냄
            yield "error", {"code": "ERROR_CODE_00011", "detail": str(e)}
        finally:
            tracker.print_usage("feedback.stream")
