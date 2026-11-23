import random
from uuid import uuid4

from langchain_core.runnables import Runnable

from app.shared.callbacks import TokenUsageTracker
from app.shared.errors import ainvoke_or_raise
from app.core.exceptions import InterviewFinishedError, InterviewNotFoundError
from app.schemas.interview import (
    InterviewAnswerRequest,
    InterviewCreateRequest,
    InterviewReportResponse,
    InterviewSessionResponse,
    InterviewTurnRecordResponse,
    InterviewTurnResponse,
    TurnGradeResponse,
)
from app.services.question_service import TOPICS

# 요청에 topics가 없을 때 무작위로 고를 주제의 수
DEFAULT_TOPIC_COUNT = 2


class InterviewService:
    def __init__(self, interview_graph: Runnable):
        self.interview_graph = interview_graph

    # 인터뷰 시작. 첫 질문 생성
    async def start(self, request: InterviewCreateRequest) -> InterviewTurnResponse:
        session_id = str(uuid4())
        # 주제 랜덤 선택
        topics = request.topics or random.sample(TOPICS, DEFAULT_TOPIC_COUNT)

        initial_state = {
            "user_name": request.user_name,
            "topics": topics,
            "topic": None,
            "topics_remaining": topics,  # ask_question에서 소모
            "question": None,
            "question_type": None,
            "answer": None,
            "depth": 0,
            "total_turns": 0,
            "last_grade": None,
            "finished": False,
            "report": None,
            "average_score": None,
            "turns": [],
        }

        result = await self._run(session_id, initial_state)
        return self._to_turn_response(session_id, result)

    async def answer(
        self, session_id: str, request: InterviewAnswerRequest
    ) -> InterviewTurnResponse:
        # 404 / 409는 그래프로 가기 전에 거른다.
        state = await self._get_state(session_id)
        if state["finished"]:
            raise InterviewFinishedError(session_id)

        # 바뀌는 값만 넣고, 나머지는 체크포인터가 복원함
        result = await self._run(session_id, {"answer": request.answer})
        return self._to_turn_response(session_id, result)

    # 문답 기록 조회
    async def get(self, session_id: str) -> InterviewSessionResponse:
        state = await self._get_state(session_id)

        return InterviewSessionResponse(
            session_id=session_id,
            user_name=state["user_name"],
            finished=state["finished"],
            turns=[
                InterviewTurnRecordResponse(
                    question=t["question"],
                    answer=t["answer"],
                    score=t["score"],
                    topic=t["topic"],
                    depth=t["depth"],
                )
                for t in state["turns"]
            ],
            report=self._to_report_response(state),
        )

    @staticmethod
    # config 딕셔너리 준비
    def _config(session_id: str) -> dict:
        return {"configurable": {"thread_id": f"interview-{session_id}"}}

    async def _get_state(self, session_id: str) -> dict:
        snapshot = await self.interview_graph.aget_state(self._config(session_id))

        if not snapshot.values:
            raise InterviewNotFoundError(session_id)
        return snapshot.values

    # 그래프 실행
    async def _run(self, session_id: str, graph_input: dict) -> dict:
        tracker = TokenUsageTracker()
        result = await ainvoke_or_raise(
            self.interview_graph,
            graph_input,
            {**self._config(session_id), "callbacks": [tracker]},
        )
        tracker.print_usage("interview")

        return result

    def _to_turn_response(self, session_id: str, state: dict) -> InterviewTurnResponse:
        turns = state["turns"]

        previous_grade = (
            TurnGradeResponse(
                score=turns[-1]["score"],
                comment=turns[-1]["comment"],
                missing_concepts=turns[-1]["missing_concepts"],
            )
            if turns
            else None
        )

        return InterviewTurnResponse(
            session_id=session_id,
            turn=state["total_turns"],
            topic=state["topic"],
            depth=state["depth"],
            previous_grade=previous_grade,
            question=state["question"],
            question_type=state["question_type"],
            finished=state["finished"],
            report=self._to_report_response(state),
        )

    @staticmethod
    def _to_report_response(state: dict) -> InterviewReportResponse | None:
        report = state["report"]
        if report is None:
            return None
        return InterviewReportResponse(
            average_score=state["average_score"],
            strong_topics=report.strong_topics,
            weak_concepts=report.weak_concepts,
            summary=report.summary,
        )
