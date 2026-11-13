from pydantic import BaseModel, Field


# 검토 LLM이 알려주는 답의 모양
class FeedbackReview(BaseModel):
    passed: bool = Field(
        description="""검토 기준을 모두 만족하면 true, 하나라도 어기면 false"""
    )
    reason: str = Field(
        description="""미통과면 어떤 기준을 어겼고 무엇을 고쳐야하는지 한두 문장으로. 통과면 빈 문자열"""
    )
