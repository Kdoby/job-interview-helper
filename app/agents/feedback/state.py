from typing import Literal, TypedDict

from app.agents.feedback.outputs import FeedbackAnalysis


# 상태 정의
class FeedbackState(TypedDict):
    question: str
    answer: str
    confidence: int
    confidence_guide: str
    feedback: str
    analysis: FeedbackAnalysis
    attempts: int
    passed: bool
    reason: str
    retry: Literal["generate", "analyze"]
