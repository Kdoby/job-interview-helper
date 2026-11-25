import operator
from typing import Annotated, TypedDict

from app.agents.coaching.outputs import RetryGrade


class AttemptRecord(TypedDict):
    attempt: int
    answer: str
    score: int
    feedback: str
    missing_concepts: list[str]
    improvements: list[str]  # 이 시도에서 직전 대비 나아진 점 (compare가 채움)


class RetryState(TypedDict):
    question: str
    answer: str  # 덮어씀 (Reducer x)
    target_score: int
    last: RetryGrade | None  # grade, 체크포인터에 저장
    next_focus: str | None  # coach
    summary: str | None
    finished: bool
    attempts: Annotated[list[AttemptRecord], operator.add]  # compare가 1개씩 붙임
