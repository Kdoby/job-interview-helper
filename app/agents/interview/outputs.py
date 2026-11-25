from pydantic import BaseModel, Field


# 답변 하나에 매기는 평가
class TurnGrade(BaseModel):
    # 노드에서 turns의 점수로 average_score 계산
    score: int = Field(
        ge=0,
        le=100,
        description="점수 기준에 따라 이번 질문에 대한 답변 내용만 보고 매긴 점수",
    )
    comment: str = Field(
        description="지원자에게 바로 보여 줄 1~2 문장의 짧은 코멘트. 다음 질문은 쓰지 않는다."
    )
    missing_concepts: list[str] = Field(
        description="이 질문에 답하려면 필요한데 빠졌거나 틀린 개념. 짧은 명사구로 쓴다(예: '페이징 메모리 처리'). 없으면 빈 리스트"
    )


class InterviewQuestion(BaseModel):
    question: str = Field(
        description="지원자에게 던질 질문 한 문장. 인사말, 칭찬, 부연 설명 없이 질문만 쓴다."
    )


class InterviewReport(BaseModel):
    strong_topics: list[str] = Field(
        description="지원자가 잘 답한 주제. 입력으로 준 주제 목록에 있는 이름 그대로만 쓴다. 없으면 빈 리스트"
    )
    weak_concepts: list[str] = Field(
        description="보완이 필요한 개념. 같은 뜻의 항목은 하나로 합치고 최대 5개, 명사구로 쓴다. 없으면 빈 리스트"
    )
    summary: str = Field(description="면접 전체 총평 3~5문장. 점수 숫자는 쓰지 않는다.")
