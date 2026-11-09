from dataclasses import dataclass


@dataclass
class Answer:
    answer_id: int  # 답변 번호(PK)
    user_name: str  # 유저 이름
    question: str  # 질문
    answer: str  # 답변
    confidence: int  # 답변에 대한 자신감
    feedback: str | None = None  # 답변에 대한 피드백
    score: int | None = None  # 답변 점수
