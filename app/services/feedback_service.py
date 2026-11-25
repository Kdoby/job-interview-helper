from typing import AsyncIterator

from langchain_core.runnables import Runnable

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
from app.shared.callbacks import TokenUsageTracker
from app.shared.errors import ainvoke_or_raise, astream_or_raise


class FeedbackService:
    def __init__(
        self,
        repository: AnswerRepository,
        feedback_graph: Runnable,
        feedback_stream_graph: Runnable,
        rubric_graph: Runnable,
    ):
        self.repository = repository
        self.feedback_graph = feedback_graph
        self.feedback_stream_graph = feedback_stream_graph
        self.rubric_graph = rubric_graph

    # 1. 답변 조회
    def find_answer(self, answer_id: int) -> Answer:
        answer = self.repository.find_by_id(answer_id)

        if answer is None:
            raise AnswerNotFoundError(answer_id)

        return answer

    def save_feedback(
        self, answer: Answer, feedback: str, score: int, missing_concepts: list[str]
    ):
        answer.feedback = feedback
        answer.score = score
        answer.missing_concepts = missing_concepts

        self.repository.save(answer)

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

    def build_rubric_input(self, answer: Answer) -> dict:
        return {
            **self.build_chain_input(answer),
            "query": answer.question,
            "rewrite_count": 0,
            "generation_count": 0,
            "reason": "",
        }

    # LLM 호출
    async def generate_feedback(self, answer_id: int) -> AiFeedbackResponse:
        answer = self.find_answer(answer_id)
        chain_input = self.build_chain_input(answer)
        tracker = TokenUsageTracker()
        config = {"callbacks": [tracker]}

        state = await ainvoke_or_raise(
            self.rubric_graph, self.build_rubric_input(answer), config
        )

        # 연관 루브릭 찾기
        if state["relevant"]:
            self.save_feedback(
                answer, state["result"].feedback, state["score"], state["missing"]
            )
            response = self.rubric_to_response(state)
        # 연관 루브릭을 못찾으면 기존 피드백 그래프 사용
        else:
            result = await ainvoke_or_raise(
                self.feedback_graph, chain_input, config=config
            )
            feedback, analysis = result["feedback"], result["analysis"]
            self.save_feedback(
                answer, feedback, analysis.score, analysis.missing_concepts
            )
            response = self.analysis_to_response(feedback, analysis)

        tracker.print_usage("feedback")
        return response

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

            self.save_feedback(
                answer, feedback, analysis.score, analysis.missing_concepts
            )
            response = self.analysis_to_response(feedback, analysis)

            # 전체 구조화된 출력
            yield "result", response.model_dump(by_alias=True)

        except AiRequestError as e:
            # 응답 코드는 이미 200이므로 error 이벤트로 알리고 끝냄
            yield "error", {"code": "ERROR_CODE_00011", "detail": str(e)}
        finally:
            tracker.print_usage("feedback.stream")

    # 피드백 그래프 결과 -> 응답 DTO
    def analysis_to_response(
        self, feedback: str, analysis: FeedbackAnalysis
    ) -> AiFeedbackResponse:
        return AiFeedbackResponse.model_validate(
            {"feedback": feedback, **analysis.model_dump(exclude={"level"})}
        )

    # 루브릭 그래프 결과 -> 응답 DTO
    def rubric_to_response(self, state: dict) -> AiFeedbackResponse:
        result = state["result"]
        return AiFeedbackResponse(
            feedback=result.feedback,
            score=state["score"],
            strengths=result.strengths,
            missing_concepts=state["missing"],
            follow_up_questions=result.follow_up_questions,
            covered_concepts=state["covered"],
            sources=[
                state["documents"][0].metadata["source"]
            ],  # 실제 채점에 사용한 문서 하나
        )
