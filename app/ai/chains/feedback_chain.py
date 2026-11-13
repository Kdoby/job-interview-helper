from langchain_openai import ChatOpenAI

from app.ai.prompts.feedback import FEEDBACK_PROMPT
from app.schemas.answer import AiFeedbackResponse


def build_feedback_chain(llm: ChatOpenAI):
    return FEEDBACK_PROMPT | llm.with_structured_output(AiFeedbackResponse)
