from pydantic import BaseModel, Field


# 질문 검증 결과
class QuestionCheck(BaseModel):
    # 주제와 적합성
    on_topic: bool = Field(
        description="주제와 적합한 질문인지 판단한다. 벗어나면 False, 적합하면 True이다."
    )
    # 근거
    reason: str = Field(
        description="주제와 적합하지 않다고 판단한 근거와 무엇을 고쳐야하는지를 저장한다. 만약 통과했다면 빈 문자열로 둔다."
    )
