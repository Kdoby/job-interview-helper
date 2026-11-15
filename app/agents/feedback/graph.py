from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.feedback.outputs import FeedbackResult, FeedbackReview
from app.agents.feedback.prompts import FEEDBACK_PROMPT, REVIEW_PROMPT, REVISION_NOTE
from app.core.thread_log import log


# 상태 정의
class FeedbackState(TypedDict):
    question: str
    answer: str
    confidence: int
    confidence_guide: str
    draft: FeedbackResult
    attempts: int
    passed: bool
    reason: str


# 그래프 조립
def build_feedback_review_graph(llm, max_reviews: int):

    # 체인 생성
    draft_chain = FEEDBACK_PROMPT | llm.with_structured_output(FeedbackResult)
    review_chain = REVIEW_PROMPT | llm.with_structured_output(FeedbackReview)
    print("[lifespan] review_chain 생성")

    # 피드백 생성 노드
    async def generate(state: FeedbackState):

        # 시도 횟수 증가
        attempts = state.get("attempts", 0) + 1
        log("feedback.generate", f"attempts={attempts}")

        # 재작성이면 reason을 프롬프트에 넣음
        reason = state.get("reason", "")
        revision_note = REVISION_NOTE.format(reason=reason) if reason else ""

        draft = await draft_chain.ainvoke(
            {
                "question": state["question"],
                "answer": state["answer"],
                "confidence": state["confidence"],
                "confidence_guide": state["confidence_guide"],
                "revision_note": revision_note,
            }
        )
        return {"draft": draft, "attempts": attempts}

    # 리뷰 노드
    async def review(state: FeedbackState):
        draft = state["draft"]

        # 1. 코드 검사
        if state["confidence"] >= 4 and len(draft.follow_up_questions) <= 0:
            reason = "자신감이 높은 지원자인데 꼬리 질문이 없다. follow_up_questions에 추가한다"
            log("feedback.review", f"코드 검사 실패: {reason}")
            return {"passed": False, "reason": reason}

        # 기대 레벨
        expected = (
            "우수" if draft.score >= 90 else "보통" if draft.score >= 70 else "부족"
        )

        if draft.level != expected:
            reason = "점수와 통과 레벨이 모순된다. 점수 루브릭과 점수 구간을 반영하여 다시 점수 구간을 산정한다."
            log("feedback.review", f"코드 검사 실패: {reason}")
            return {"passed": False, "reason": reason}

        # 2. LLM 검토
        result = await review_chain.ainvoke(
            {
                "question": state["question"],
                "answer": state["answer"],
                "confidence": state["confidence"],
                "feedback": draft.feedback,
                "score": draft.score,
            }
        )

        # LLM 판정 결과
        log("feedback.review", f"passed={result.passed}, reason={result.reason}")
        return {"passed": result.passed, "reason": result.reason}

    # 리뷰 라우터
    def route_after_review(state: FeedbackState):
        if state["passed"] or state["attempts"] >= max_reviews:
            return END

        # 피드백 작성 노드로 돌아감
        return "generate"

    # 그래프 조립
    builder = StateGraph(FeedbackState)

    # 노드 등록
    builder.add_node("generate", generate)
    builder.add_node("review", review)

    # 엣지 등록
    builder.add_edge(START, "generate")
    builder.add_edge("generate", "review")
    builder.add_conditional_edges("review", route_after_review, ["generate", END])

    return builder.compile()
