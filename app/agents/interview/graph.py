from dataclasses import dataclass

from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph

from app.agents.interview.outputs import InterviewQuestion, InterviewReport, TurnGrade
from app.agents.interview.prompts import (
    ASK_QUESTION_PROMPT,
    FOLLOW_UP_PROMPT,
    GRADE_PROMPT,
    HINT_PROMPT,
    REPORT_PROMPT,
)
from app.agents.interview.state import InterviewState, Turn
from app.core.thread_log import log


@dataclass
class InterviewChains:
    ask_question: Runnable
    grade: Runnable
    follow_up: Runnable
    hint: Runnable
    report: Runnable


def build_interview_chains(llm) -> InterviewChains:
    question_llm = llm.with_structured_output(InterviewQuestion)

    return InterviewChains(
        ask_question=ASK_QUESTION_PROMPT | question_llm,
        grade=GRADE_PROMPT | llm.with_structured_output(TurnGrade),
        follow_up=FOLLOW_UP_PROMPT | question_llm,
        hint=HINT_PROMPT | question_llm,
        report=REPORT_PROMPT | llm.with_structured_output(InterviewReport),
    )


# list -> str
def join_or_none(items: list[str]) -> str:
    return ", ".join(items) or "없음"


# turn 정보 출력 포맷
def format_turns(turns: list[Turn]) -> str:
    if not turns:
        return "없음"
    return "\n".join(
        f"[{t['turn']}] {t['topic']} | {t['question_type']} | Q: {t['question']} | "
        f"A: {t['answer']} | {t['score']}점 | 빠진 개념: {', '.join(t['missing_concepts']) or '없음'}"
        for t in turns
    )


# 평균 점수 구하기
def average(scores: list[int]) -> int:
    return round(sum(scores) / len(scores)) if scores else 0


def build_interview_graph(llm, max_depth, max_turns, follow_up_score, checkpointer):

    chains = build_interview_chains(llm)

    # 새 주제 시작
    async def ask_question(state: InterviewState) -> dict:

        topic = state["topics_remaining"][0]

        result = await chains.ask_question.ainvoke({"topic": topic})

        return {
            "topic": topic,
            "topics_remaining": state["topics_remaining"][1:],  # 맨 앞 주제만 자름
            "question": result.question,
            "depth": 0,
            "question_type": "MAIN",
            "total_turns": state["total_turns"] + 1,
        }

    async def grade_answer(state: InterviewState) -> dict:

        # 현재 답변 평가
        result: TurnGrade = await chains.grade.ainvoke(
            {
                "topic": state["topic"],
                "question_type": state["question_type"],
                "question": state["question"],
                "answer": state["answer"],
            }
        )

        # 여기서 Turn을 생성
        turn: Turn = {
            "turn": state["total_turns"],
            "topic": state["topic"],
            "question": state["question"],
            "question_type": state["question_type"],
            "answer": state["answer"],
            "depth": state["depth"],
            "score": result.score,
            "comment": result.comment,
            "missing_concepts": result.missing_concepts,
        }

        log("interview.grade_answer", f"{turn['turn']}번 점수: {result.score}")
        return {"last_grade": result, "turns": [turn]}

    async def ask_follow_up(state: InterviewState) -> dict:

        # 현재 주제에 대한 turn 목록
        history = [t for t in state["turns"][:-1] if t["topic"] == state["topic"]]

        result = await chains.follow_up.ainvoke(
            {
                "topic": state["topic"],
                "history": format_turns(history),
                "question": state["question"],
                "answer": state["answer"],
            }
        )

        log("interview.ask_follow_up", result.question)
        return {
            "question": result.question,
            "question_type": "FOLLOW_UP",
            "depth": state["depth"] + 1,
            "total_turns": state["total_turns"] + 1,
        }

    async def ask_hint_question(state: InterviewState) -> dict:

        result: InterviewQuestion = await chains.hint.ainvoke(
            {
                "topic": state["topic"],
                "question": state["question"],
                "answer": state["answer"],
                "missing_concepts": join_or_none(state["last_grade"].missing_concepts),
            }
        )

        log("interview.ask_hint_question", f"힌트 {result.question}")

        return {
            "question": result.question,
            "question_type": "HINT",
            "depth": state["depth"] + 1,
            "total_turns": state["total_turns"] + 1,
        }

    async def final_report(state: InterviewState) -> dict:

        turns = state["turns"]

        # 각 주제별 점수
        scores_by_topic: dict[str, list[int]] = {}
        for t in turns:
            scores_by_topic.setdefault(t["topic"], []).append(t["score"])
        topic_scores = join_or_none(
            [f"{topic}: {average(scores)}" for topic, scores in scores_by_topic.items()]
        )
        result: InterviewReport = await chains.report.ainvoke(
            {
                "topics": join_or_none(state["topics"]),
                "topics_remaining": join_or_none(state["topics_remaining"]),
                "interview_follow_up_score": follow_up_score,
                "topic_scores": topic_scores,
                "history": format_turns(turns),
            }
        )

        average_score = average([t["score"] for t in turns])
        log(
            "interview.final_report",
            f"평균 {average_score}점, 강한 주제 {result.strong_topics}",
        )

        return {
            "report": result,
            "average_score": average_score,
            "finished": True,
            "question": None,
            "question_type": None,
        }

    # 첫 질문 생성 여부 결정 라우터
    def entry(state: InterviewState):
        if state["answer"]:
            return "grade_answer"
        return "ask_question"

    def route(state: InterviewState):
        # 이전 turn의 grade
        grade = state["last_grade"]
        can_go_deeper = state["depth"] < max_depth

        # 문항 상한
        if state["total_turns"] >= max_turns:
            return "final_report"
        # 점수 높음
        if grade.score >= follow_up_score and can_go_deeper:
            return "ask_follow_up"
        # 점수 낮음, 빠진 개념 존재
        if grade.score < follow_up_score and grade.missing_concepts and can_go_deeper:
            return "ask_hint_question"
        # 남은 주제 있음
        if state["topics_remaining"]:
            return "ask_question"
        # 남은 주제 없음
        return "final_report"

    builder = StateGraph(InterviewState)

    builder.add_node("ask_question", ask_question)
    builder.add_node("grade_answer", grade_answer)
    builder.add_node("ask_follow_up", ask_follow_up)
    builder.add_node("ask_hint_question", ask_hint_question)
    builder.add_node("final_report", final_report)

    builder.add_conditional_edges(START, entry, ["ask_question", "grade_answer"])
    builder.add_conditional_edges(
        "grade_answer",
        route,
        ["ask_question", "ask_follow_up", "ask_hint_question", "final_report"],
    )

    builder.add_edge("ask_question", END)
    builder.add_edge("ask_follow_up", END)
    builder.add_edge("ask_hint_question", END)
    builder.add_edge("final_report", END)

    return builder.compile(checkpointer=checkpointer)
