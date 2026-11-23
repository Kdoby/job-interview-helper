import operator
from typing import Annotated, Literal, TypedDict

from app.agents.interview.outputs import InterviewReport, TurnGrade

QuestionType = Literal["MAIN", "FOLLOW_UP", "HINT"]


# 답변이 끝난 한 턴
class Turn(TypedDict):
    turn: int  # 질문 순서 (1부터 시작)
    topic: str
    question: str
    question_type: QuestionType
    answer: str
    depth: int
    score: int
    comment: str
    missing_concepts: list[str]  # 해결 여부는 LLM이 판단


class InterviewState(TypedDict):
    # == 세션 정보 ==
    user_name: str
    topics: list[str]  # 시작할 때 정한 전체 주제

    # == 진행 상태 ==
    topic: str | None
    topics_remaining: list[str]
    # 현재 질문
    question: str | None
    # 지금 답을 기다리는 질문 하나(current_question의 유형)
    question_type: QuestionType | None
    answer: str | None  # 이번 요청의 답변
    depth: int
    total_turns: int  # 지금까지 던진 질문 수(AUTO_INCREMENT 느낌)

    # == 결과 ==
    last_grade: TurnGrade | None
    finished: bool
    report: InterviewReport | None
    average_score: int | None

    # == 누적 ==
    turns: Annotated[list[Turn], operator.add]  # 지나간 답변 누적
