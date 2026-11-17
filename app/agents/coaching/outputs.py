from pydantic import BaseModel, Field


class RetryGrade(BaseModel):
    score: int = Field(
        ge=0,
        le=100,
        description="점수 기준에 따라 이번 답변 내용만 보고 매긴 점수. 이전 시도보다 나아졌다고 점수를 더 주지 않는다.",
    )
    feedback: str = Field(
        description="이번 답변에 대한 3~5문장 피드백. 꼬리 질문이나 다음 과제는 쓰지 않는다."
    )
    missing_concepts: list[str] = Field(
        description="답변에 빠졌거나 틀리게 설명한 핵심 개념의 이름. "
        "문장이 아닌 짧은 명사구로 쓴다(예: 'B-Tree 구조', '쓰기 성능 저하'). "
        "없으면 빈 리스트."
    )


class CompareResult(BaseModel):
    improvements: list[str] = Field(
        description="직전 답변에는 없었거나 틀렸는데 이번 답변에서 새로 맞게 설명한 점. "
        "항목마다 짧은 한 문장(예: '원인(지연 로딩)을 설명함'). 나아진 점이 없으면 빈 리스트"
    )


class CoachResult(BaseModel):
    next_focus: str = Field(
        description='다음 시도에서 보완할 딱 한가지를 "~를 설명해 보세요"꼴의 한 문장으로 쓴다. 모범 답안은 쓰지 않는다.'
    )


class CoachSummary(BaseModel):
    summary: str = Field(
        description="1차부터 마지막 시도까지 무엇을 차례로 보완했는지 2~4문장. 점수는 입력으로 받은 점수 흐름을 그대로만 인용한다."
    )
