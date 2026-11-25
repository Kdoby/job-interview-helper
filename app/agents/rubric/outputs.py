from pydantic import BaseModel, Field


# 특정 질문에 대해 참고할 루브릭 문서를 찾을 때, 연관성 판단
class RelevanceGrade(BaseModel):
    reason: str = Field(
        description="질문의 핵심 주제와 루브릭의 주제를 비교한 판정 근거. 한 문장"
    )
    relevant: bool = Field(
        description="루브릭이 면접 질문과 같은 주제를 다루면 true, 단어가 겹쳐도 묻는 내용이 다르면 false"
    )


# 유저의 답변 개념 채점
class ConceptMatch(BaseModel):
    covered: list[str] = Field(
        description="<concepts> 목록 중 답변이 정확하게 설명한 개념. 목록의 이름을 글자 그대로 쓴다. "
        "이름만 언급하고 틀리게 설명했으면 넣지 않는다. 없으면 빈 리스트."
    )


# 관련 청크가 없는 경우 재작성
class RewrittenQuery(BaseModel):
    query: str = Field(
        description="루브릭 검색에 쓸 새 검색어. 기술 주제 이름과 핵심 용어로 한 줄"
    )


# rubric 문서 기반 피드백
class RubricFeedback(BaseModel):
    feedback: str = Field(
        description="연관된 루브릭 문서를 기반으로 사용자 답변에 대한 피드백 작성. 1000자 이하 줄글, 꼬리 질문은 쓰지 않는다."
    )
    strengths: list[str] = Field(
        description="연관 루브릭 문서의 핵심 개념과 사용자 답변을 대조해 매칭되는 부분. 항목마다 한 문장, 없으면 빈 리스트."
    )
    follow_up_questions: list[str] = Field(
        description="루브릭 문서를 기반으로 답변 내용을 더 깊이 검증하는 꼬리 질문. 자신감이 높을 때(4 이상)만 1~2개 쓰고, 그 외에는 빈 리스트."
    )


# 피드백 검토
class GroundedCheck(BaseModel):
    grounded: bool = Field(
        description="루브릭에 있는 내용을 근거로 피드백을 잘 작성했으면 True, 아니면 False."
    )
    reason: str = Field(
        description="피드백이 루브릭을 근거로 작성되지 않았다고 판단한 근거. 통과면 빈 문자열."
    )
