from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import END, START, StateGraph

from app.agents.feedback.outputs import FeedbackAnalysis, FeedbackReview
from app.agents.feedback.prompts import (
    ANALYZE_PROMPT,
    REVIEW_PROMPT,
    REVISION_NOTE,
    WRITE_PROMPT,
)
from app.agents.feedback.state import FeedbackState
from app.core.thread_log import log


# 그래프 조립
def build_feedback_review_graph(llm, max_reviews: int):

    # 체인 생성
    write_chain = WRITE_PROMPT | llm | StrOutputParser()
    analyze_chain = ANALYZE_PROMPT | llm.with_structured_output(FeedbackAnalysis)
    review_chain = REVIEW_PROMPT | llm.with_structured_output(FeedbackReview)
    print("[lifespan] review_chain 생성")

    # 피드백 초안 작성 노드
    async def generate(state: FeedbackState):

        log("feedback.generate", "feedback 작성 시작...")

        # 재작성이면 reason을 프롬프트에 넣음
        reason = state.get("reason", "")
        revision_note = (
            REVISION_NOTE.format(reason=reason)
            if state.get("retry") == "generate"
            else ""
        )

        feedback = await write_chain.ainvoke(
            {
                "question": state["question"],
                "answer": state["answer"],
                "confidence": state["confidence"],
                "confidence_guide": state["confidence_guide"],
                "revision_note": revision_note,
            }
        )
        return {"feedback": feedback}

    # 피드백 채점 및 구조화 노드
    async def analyze(state: FeedbackState):

        # 시도 횟수 증가
        attempts = state.get("attempts", 0) + 1
        log("feedback.analyze", f"attempts={attempts}")

        reason = state.get("reason", "")
        revision_note = (
            REVISION_NOTE.format(reason=reason)
            if state.get("retry") == "analyze"
            else ""
        )

        analysis: FeedbackAnalysis = await analyze_chain.ainvoke(
            {
                "question": state["question"],
                "answer": state["answer"],
                "confidence": state["confidence"],
                "feedback": state["feedback"],
                "revision_note": revision_note,
            }
        )
        return {"analysis": analysis, "attempts": attempts}

    # 리뷰 노드
    async def review(state: FeedbackState):

        analysis = state["analysis"]

        # 1. 코드 검사
        if state["confidence"] >= 4 and len(analysis.follow_up_questions) <= 0:
            reason = "자신감이 높은 지원자인데 꼬리 질문이 없다. follow_up_questions에 추가한다"
            log("feedback.review", f"코드 검사 실패: {reason}")
            return {"passed": False, "reason": reason, "retry": "analyze"}

        # 기대 레벨
        expected = (
            "우수"
            if analysis.score >= 90
            else "보통"
            if analysis.score >= 70
            else "부족"
        )

        if analysis.level != expected:
            reason = "점수와 통과 레벨이 모순된다. 점수 루브릭과 점수 구간을 반영하여 다시 점수 구간을 산정한다."
            log("feedback.review", f"코드 검사 실패: {reason}")
            return {"passed": False, "reason": reason, "retry": "analyze"}

        # 2. LLM 검토
        result = await review_chain.ainvoke(
            {
                "question": state["question"],
                "answer": state["answer"],
                "confidence": state["confidence"],
                "feedback": state["feedback"],
                "score": analysis.score,
            }
        )

        # LLM 판정 결과
        log("feedback.review", f"passed={result.passed}, reason={result.reason}")
        return {"passed": result.passed, "reason": result.reason, "retry": "generate"}

    # 리뷰 라우터
    def route_after_review(state: FeedbackState):
        if state["passed"] or state["attempts"] >= max_reviews:
            return END

        # generate or analyze 노드로 돌아감
        return state["retry"]

    # 그래프 조립
    builder = StateGraph(FeedbackState)

    # 노드 등록
    builder.add_node("generate", generate)
    builder.add_node("analyze", analyze)
    builder.add_node("review", review)

    # 엣지 등록
    builder.add_edge(START, "generate")
    builder.add_edge("generate", "analyze")
    builder.add_edge("analyze", "review")
    builder.add_conditional_edges(
        "review", route_after_review, ["generate", "analyze", END]
    )

    return builder.compile()
