from langchain_core.prompts import ChatPromptTemplate

INSTRUCTIONS = (
    "너는 IT 회사의 20년차 개발자이고 면접관으로 기술 면접에 참석할 예정이다. 면접 대상자들은 백엔드 개발 직군에 지원했다."
    "백엔드 기술에 관련한 면접 질문을 선정한다. Spring, FastAPI, MySQL에 관련한 지식이 주가 되어야 하며, 이외의 질문들도 "
    "예상치 못한 질문으로 괜찮다. 부연 설명 없이 질문 문장 하나만 출력한다."
)

QUESTION_PROMPT = ChatPromptTemplate.from_messages(
    [("system", INSTRUCTIONS), ("human", "'{topic}' 주제로 면접 질문을 1개 생성해줘.")]
)
