from app.shared.callbacks import TokenUsageTracker
from app.shared.errors import ainvoke_or_raise
from app.core.exceptions import (
    AnswerNotFoundError,
    FeedbackNotReadyError,
    RetryLimitExceededError,
)
from app.repositories.answer_repository import AnswerRepository
from app.schemas.answer import AnswerRetryResponse

from langchain_core.runnables import Runnable


class CoachingService:
    def __init__(
        self,
        repository: AnswerRepository,
        coaching_graph: Runnable,
        target_score: int,
        max_attempts: int,
    ):
        self.repository = repository
        self.coaching_graph = coaching_graph
        self.target_score = target_score
        self.max_attempts = max_attempts

    async def retry(self, answer_id: int, new_answer: str) -> AnswerRetryResponse:
        # 404 검사
        answer = self.repository.find_by_id(answer_id)
        if answer is None:
            raise AnswerNotFoundError(answer_id)

        config = {"configurable": {"thread_id": f"retry-{answer_id}"}}
        # 특정 스레드의 체크포인트나 현재 상태(State) 조회, await가 .values 보다 먼저 실행
        state = (await self.coaching_graph.aget_state(config)).values

        if not state:
            # 409 검사
            if answer.score is None:
                raise FeedbackNotReadyError(answer_id)
            graph_input = {
                "question": answer.question,
                "answer": new_answer,
                "target_score": self.target_score,
                "attempts": [
                    {
                        "attempt": 1,
                        "answer": answer.answer,  # 원래 답변
                        "score": answer.score,
                        "feedback": answer.feedback,
                        "missing_concepts": answer.missing_concepts,
                        "improvements": [],
                    }
                ],
            }
        else:
            # 2번째 retry부터 재답변 가능 여부 체크
            if state.get("finished") or len(state["attempts"]) >= self.max_attempts:
                raise RetryLimitExceededError(answer_id)
            # 2번째 retry부터는 상태를 체크포인터에 저장하고 수정한 answer만 보냄
            graph_input = {"answer": new_answer}

        tracker = TokenUsageTracker()
        result = await ainvoke_or_raise(
            self.coaching_graph, graph_input, {**config, "callbacks": [tracker]}
        )
        tracker.print_usage("coaching")

        return self.to_response(result)

    def to_response(self, result: dict) -> AnswerRetryResponse:
        cur, prev = result["attempts"][-1], result["attempts"][-2]
        finished = result.get("finished", False)

        return AnswerRetryResponse(
            attempt=cur["attempt"],
            score=cur["score"],
            score_delta=cur["score"] - prev["score"],
            feedback=cur["feedback"],
            missing_concepts=cur["missing_concepts"],
            improvements=cur["improvements"],
            next_focus=None if finished else result.get("next_focus"),
            finished=finished,
            summary=result.get("summary") if finished else None,
        )
