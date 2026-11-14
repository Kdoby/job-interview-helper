import re
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.ai.chains.question_chain import build_question_chain
from app.ai.outputs.question import QuestionCheck
from app.ai.prompts.question import QUESTION_CHECK_PROMPT, REVISION_NOTE
from app.core.thread_log import log


class QuestionState(TypedDict):
    topic: str
    question: str
    check_reason: str
    attempts: int
    passed: bool


def build_question_check_graph(llm: ChatOpenAI, max_regenerations):

    question_chain = build_question_chain(llm)
    question_check_chain = QUESTION_CHECK_PROMPT | llm.with_structured_output(
        QuestionCheck
    )
    print("[lifespan] check_chain 생성")

    # 질문 생성 노드
    def generate(state: QuestionState) -> dict:

        # 시도 횟수 증가
        attempts = state.get("attempts", 0) + 1
        log("question_check", f"attempts={attempts}")

        # 재생성이면 근거 삽입, 아니면 빈 문자열
        check_reason = state.get("check_reason", "")
        revision_note = (
            REVISION_NOTE.format(reason=check_reason) if check_reason else ""
        )

        result = question_chain.invoke(
            {"topic": state["topic"], "revision_note": revision_note}
        )

        return {"question": result, "attempts": attempts}

    # 질문 검증 노드
    def validate(state: QuestionState) -> dict:

        q = state["question"].strip()
        multi_line = "\n" in q
        multi_sentence = re.search(r"[.?!]\s+\S", q) is not None

        # 1. 코드 검사
        if multi_line or multi_sentence:
            reason = "한 문장으로 끝나는 질문만 해야한다."
            log("question_check", f"코드 검사 실패: {reason}")
            return {"passed": False, "check_reason": reason}
        # 2. LLM 검사 (의미 기반)
        result = question_check_chain.invoke(
            {"topic": state["topic"], "question": state["question"]}
        )

        log(
            "question_check",
            f"passed={result.on_topic}, check_reason={result.reason}",
        )
        return {"passed": result.on_topic, "check_reason": result.reason}

    def route_after_validate(state: QuestionState) -> str:
        if state["passed"] or state["attempts"] >= max_regenerations:
            return END

        return "generate"

    builder = StateGraph(QuestionState)

    # 노드 추가
    builder.add_node("generate", generate)
    builder.add_node("validate", validate)

    # 엣지 추가
    builder.add_edge(START, "generate")
    builder.add_edge("generate", "validate")
    builder.add_conditional_edges("validate", route_after_validate, ["generate", END])

    return builder.compile()
