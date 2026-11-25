from pydantic import Field

from app.schemas.base import CamelModel


# 면접 시작 요청 DTO
class InterviewCreateRequest(CamelModel):
    user_name: str = Field(min_length=1, max_length=10)
    topics: list[str] | None = Field(default=None, min_length=1, max_length=3)


# 지금 질문에 대한 답변 제출
class InterviewAnswerRequest(CamelModel):
    answer: str = Field(min_length=1, max_length=300)


# ==========================================
# 응답 조각
# ==========================================


# 방금 낸 답변의 채점 결과
class TurnGradeResponse(CamelModel):
    score: int
    comment: str
    missing_concepts: list[str]


# 면접이 끝났을 때의 종합 리포트
class InterviewReportResponse(CamelModel):
    average_score: int  # 파이썬이 계산한 값
    strong_topics: list[str]
    weak_concepts: list[str]
    summary: str


# 지나간 기록 문답 한 줄
class InterviewTurnRecordResponse(CamelModel):
    question: str
    answer: str
    score: int
    topic: str
    depth: int


# ==========================================
# 최상위 응답
# ==========================================


# 이번 한 턴 조회 전용. 시작 요청과 답변 요청이 같이 쓰는 응답 (직전 답변 결과 + 다음 질문)
class InterviewTurnResponse(CamelModel):
    session_id: str
    turn: int
    topic: str
    depth: int
    previous_grade: TurnGradeResponse | None = None  # 이전 문답에 대한 평가
    question: str | None = None  # 다음 질문
    question_type: str | None = None  # 다음 질문 타입
    finished: bool
    report: InterviewReportResponse | None = None


# 기록 조회 전용. 세션 전체를 한 번에 보여줌
class InterviewSessionResponse(CamelModel):
    session_id: str
    user_name: str
    finished: bool
    turns: list[InterviewTurnRecordResponse]
    report: InterviewReportResponse | None = None
