from dataclasses import dataclass

from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph

from app.agents.rubric.outputs import (
    ConceptMatch,
    GroundedCheck,
    RelevanceGrade,
    RewrittenQuery,
    RubricFeedback,
)
from app.agents.rubric.prompts import (
    MATCH_PROMPT,
    RELEVANCE_PROMPT,
    REVISION_NOTE,
    REWRITE_PROMPT,
    VERIFY_PROMPT,
    WRITE_PROMPT,
)
from app.agents.rubric.state import RubricState
from app.core.thread_log import log
from app.shared.data import parse_concepts


@dataclass
class RubricChains:
    relevance: Runnable
    rewrite: Runnable
    match: Runnable
    write: Runnable
    verify: Runnable


def build_rubric_chains(llm) -> RubricChains:

    relevance = RELEVANCE_PROMPT | llm.with_structured_output(RelevanceGrade)
    rewrite = REWRITE_PROMPT | llm.with_structured_output(RewrittenQuery)
    match = MATCH_PROMPT | llm.with_structured_output(ConceptMatch)
    write = WRITE_PROMPT | llm.with_structured_output(RubricFeedback)
    verify = VERIFY_PROMPT | llm.with_structured_output(GroundedCheck)

    return RubricChains(
        relevance=relevance, rewrite=rewrite, match=match, write=write, verify=verify
    )


def build_rubric_graph(llm, retriever, max_rewrites: int, max_generations: int):
    chains = build_rubric_chains(llm)

    async def retrieve(state: RubricState) -> dict:
        docs = await retriever.ainvoke(state["query"])

        log("rubric.retrieve", f"{[d.metadata['source'] for d in docs]}")

        return {"documents": docs}

    # 연관성 비교
    async def relevance(state: RubricState) -> dict:
        docs = state["documents"]
        # abatch는 입력 순서대로 결과를 돌려주어 유사도 순서가 유지됨
        grades = await chains.relevance.abatch(
            [{"question": state["question"], "rubric": d.page_content} for d in docs]
        )

        # 문서별 판정 근거
        for d, g in zip(docs, grades):
            log(
                "rubric.relevance", f"{d.metadata['source']}: {g.relevant} / {g.reason}"
            )

        kept = [d for d, g in zip(docs, grades) if g.relevant]

        log("rubric.relevance", f"{len(kept)}/{len(docs)}개 통과")

        return {"documents": kept, "relevant": bool(kept)}

    # 연관 문서를 찾기 위한 질문 재작성
    async def rewrite(state: RubricState) -> dict:
        result = await chains.rewrite.ainvoke(
            {"question": state["question"], "query": state["query"]}
        )

        log(
            "rubric.rewrite",
            f"검색어 재작성({state['rewrite_count'] + 1}회): {result.query}",
        )

        return {"query": result.query, "rewrite_count": state["rewrite_count"] + 1}

    # 연관된 문서와 비교 매칭
    async def match(state: RubricState) -> dict:
        # relevance를 통과한 것 중 유사도가 가장 높은 하나
        rubric = state["documents"][0]
        concepts = parse_concepts(rubric)
        result = await chains.match.ainvoke(
            {
                "question": state["question"],
                "answer": state["answer"],
                "rubric": rubric.page_content,
                "concepts": ", ".join(concepts),
            }
        )

        log("rubric.match", f"{rubric.metadata['source']} / covered: {result.covered}")

        return {"concepts": concepts, "covered": result.covered}

    # 연관 문서의 내용을 기반으로 답변에 점수 매기기
    async def score_by_code(state: RubricState) -> dict:
        concepts = state["concepts"]
        said = set(state["covered"])
        # 놓치지 않은 개념
        covered = [c for c in concepts if c in said]
        # 놓친 개념
        missing = [c for c in concepts if c not in said]
        score = round(len(covered) / len(concepts) * 100) if concepts else 0

        log("rubric.score_by_code", f"{len(covered)}/{len(concepts)} → {score}점")

        return {"covered": covered, "missing": missing, "score": score}

    # 연관 문서 기반으로 답변에 대한 피드백 작성
    async def write(state: RubricState) -> dict:
        note = (
            REVISION_NOTE.format(reason=state["reason"])
            if state["generation_count"] > 0
            else ""
        )
        result: RubricFeedback = await chains.write.ainvoke(
            {
                "question": state["question"],
                "answer": state["answer"],
                "confidence": state["confidence"],
                "confidence_guide": state["confidence_guide"],
                "rubric": state["documents"][0].page_content,
                "covered": ", ".join(state["covered"]) or "없음",
                "missing": ", ".join(state["missing"]) or "없음",
                "revision_note": note,
            }
        )

        log("rubric.write", f"{state['generation_count'] + 1}회차 작성")

        return {"result": result, "generation_count": state["generation_count"] + 1}

    # 피드백 검증
    async def verify(state: RubricState) -> dict:
        check: GroundedCheck = await chains.verify.ainvoke(
            {
                "question": state["question"],
                "answer": state["answer"],
                "rubric": state["documents"][0].page_content,
                "covered": ", ".join(state["covered"]) or "없음",
                "missing": ", ".join(state["missing"]) or "없음",
                "feedback": state["result"].feedback,
            }
        )

        log("rubric.verify", f"grounded={check.grounded} {check.reason}")

        return {"grounded": check.grounded, "reason": check.reason}

    # 연관 루브릭을 찾기 위한 질문(쿼리) 재작성
    def route_after_relevance(state: RubricState) -> str:
        if state["relevant"]:
            return "match"
        if state["rewrite_count"] < max_rewrites:
            return "rewrite"
        return END

    # 피드백 재작성
    def route_after_verify(state: RubricState) -> str:
        if state["grounded"] or state["generation_count"] >= max_generations:
            return END
        return "write"

    builder = StateGraph(RubricState)

    builder.add_node("retrieve", retrieve)
    builder.add_node("relevance", relevance)
    builder.add_node("rewrite", rewrite)
    builder.add_node("match", match)
    builder.add_node("score_by_code", score_by_code)
    builder.add_node("write", write)
    builder.add_node("verify", verify)

    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "relevance")
    builder.add_conditional_edges(
        "relevance", route_after_relevance, ["match", "rewrite", END]
    )
    builder.add_edge("rewrite", "retrieve")
    builder.add_edge("match", "score_by_code")
    builder.add_edge("score_by_code", "write")
    builder.add_edge("write", "verify")
    builder.add_conditional_edges("verify", route_after_verify, ["write", END])

    return builder.compile()
