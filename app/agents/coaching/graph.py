from dataclasses import dataclass

from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph

from app.agents.coaching.outputs import (
    CoachResult,
    CoachSummary,
    CompareResult,
    RetryGrade,
)
from app.agents.coaching.prompts import (
    COACH_PROMPT,
    COMPARE_PROMPT,
    GRADE_PROMPT,
    SUMMARY_PROMPT,
)
from app.agents.coaching.state import AttemptRecord, RetryState
from app.core.thread_log import log


@dataclass
class CoachingChains:
    grade: Runnable
    compare: Runnable
    coach: Runnable
    summary: Runnable


def build_coaching_chains(llm) -> CoachingChains:
    # 이번 답변 점수 매기기
    grade_chain = GRADE_PROMPT | llm.with_structured_output(RetryGrade)
    # 이전 답변보다 발전한 점
    compare_chain = COMPARE_PROMPT | llm.with_structured_output(CompareResult)
    # 보완할 점
    coach_chain = COACH_PROMPT | llm.with_structured_output(CoachResult)
    # 코칭 요약 (각 시도별 요약)
    summary_chain = SUMMARY_PROMPT | llm.with_structured_output(CoachSummary)

    return CoachingChains(
        grade=grade_chain,
        compare=compare_chain,
        coach=coach_chain,
        summary=summary_chain,
    )


def build_coaching_graph(llm, max_attempts: int, checkpointer):
    chains = build_coaching_chains(llm)

    async def grade(state: RetryState) -> dict:
        result = await chains.grade.ainvoke(
            {"question": state["question"], "answer": state["answer"]},
        )

        log("coaching.grade", f"재답변 점수: {result.score}")

        return {"last": result}

    async def compare(state: RetryState) -> dict:
        prev: AttemptRecord = state["attempts"][-1]  # 직전 시도
        last: RetryGrade = state["last"]  # 이번 시도의 채점 결과

        # 이전 답변보다 나아진 점
        result: CompareResult = await chains.compare.ainvoke(
            {
                "question": state["question"],
                "previous_answer": prev["answer"],
                "previous_missing_concepts": prev["missing_concepts"],
                "answer": state["answer"],
                "missing_concepts": last.missing_concepts or "없음",
            }
        )

        record: AttemptRecord = {
            "attempt": prev["attempt"] + 1,
            "answer": state["answer"],
            "score": last.score,
            "feedback": last.feedback,
            "missing_concepts": last.missing_concepts,
            "improvements": result.improvements,
        }

        log("coaching.compare", f"원본 기록과 비교 후 나아진 점:{result.improvements}")

        # 리듀서로 누적
        return {"attempts": [record]}

    async def coach(state: RetryState):

        last: RetryGrade = state["last"]  # 이번 시도의 채점 결과

        result = await chains.coach.ainvoke(
            {
                "question": state["question"],
                "answer": state["answer"],
                "missing_concepts": last.missing_concepts,
                "previous_focus": state.get("next_focus") or "없음",
            }
        )

        log("coaching.coach", f"보완할 점:{result.next_focus}")

        return {"next_focus": result.next_focus}

    async def summary(state: RetryState):

        score_path = " -> ".join(str(a["score"]) for a in state["attempts"])
        end_reason = (
            "목표 점수 도달"
            if state["last"].score >= state["target_score"]
            else "시도 상한"
        )
        attempts_text = "\n".join(
            f"[{a['attempt']}차] {a['score']}점 / 개선점: {', '.join(a['improvements']) or '없음'}"
            f" / 빠진 개념: {', '.join(a['missing_concepts']) or '없음'}"
            for a in state["attempts"]
        )

        result = await chains.summary.ainvoke(
            {
                "question": state["question"],
                "score_path": score_path,
                "end_reason": end_reason,
                "attempts_text": attempts_text,
            }
        )

        log("coaching.summary", f"요약: {result.summary}")

        return {"finished": True, "summary": result.summary, "next_focus": None}

    def route_after_compare(state: RetryState):
        if (
            state["last"].score >= state["target_score"]
            or len(state["attempts"]) >= max_attempts
        ):
            return "summary"
        return "coach"

    builder = StateGraph(RetryState)

    builder.add_node("grade", grade)
    builder.add_node("compare", compare)
    builder.add_node("coach", coach)
    builder.add_node("summary", summary)

    builder.add_edge(START, "grade")
    builder.add_edge("grade", "compare")
    builder.add_conditional_edges("compare", route_after_compare, ["summary", "coach"])
    builder.add_edge("coach", END)
    builder.add_edge("summary", END)

    return builder.compile(checkpointer=checkpointer)
