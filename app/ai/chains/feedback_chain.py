from langchain_openai import ChatOpenAI

from app.ai.outputs.feedback import FeedbackResult
from app.ai.prompts.feedback import FEEDBACK_PROMPT


def build_feedback_chain(llm: ChatOpenAI):
    return FEEDBACK_PROMPT | llm.with_structured_output(FeedbackResult)
