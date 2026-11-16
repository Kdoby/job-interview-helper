from typing import Literal

from pydantic import BaseModel, Field


class FeedbackResult(BaseModel):
    feedback: str = Field(
        description="""답변에 대한 면접관의 피드백 줄글(1000자 이하). 
        자신감에 따른 말투 지시를 따른다. 
        꼬리 질문은 여기에 쓰지 않고 follow_up_questions에만 담는다."""
    )


class FeedbackAnalysis(BaseModel):
    score: int = Field(
        ge=0,
        le=100,
        description="""점수 기준에 따라 답변 내용만 보고 매긴 0~100 사이 점수.
        자신감은 점수에 반영하지 않는다.""",
    )
    strengths: list[str] = Field(
        description="답변에서 잘한 점. 항목마다 한 문장으로 쓴다. 잘한 점이 없으면 빈 리스트."
    )
    missing_concepts: list[str] = Field(
        description="답변에 빠졌거나 틀리게 설명한 핵심 개념의 이름. "
        "문장이 아닌 짧은 명사구로 쓴다(예: 'B-Tree 구조', '쓰기 성능 저하'). "
        "없으면 빈 리스트."
    )
    follow_up_questions: list[str] = Field(
        description="답변 내용을 더 깊이 검증하는 꼬리 질문. 자신감이 높을 때(4 이상)만 1~2개 쓰고, 그 외에는 빈 리스트."
    )
    level: Literal["부족", "보통", "우수"] = Field(
        description="score에 맞는 수준. 90~100은 '우수', 70~89는 '보통', 0~69는 '부족'."
    )


# 검토 LLM이 알려주는 답의 모양
class FeedbackReview(BaseModel):
    passed: bool = Field(
        description="""검토 기준을 모두 만족하면 true, 하나라도 어기면 false"""
    )
    reason: str = Field(
        description="""미통과면 어떤 기준을 어겼고 무엇을 고쳐야하는지 한두 문장으로. 통과면 빈 문자열"""
    )
