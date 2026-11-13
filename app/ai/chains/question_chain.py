from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from app.ai.prompts.question import QUESTION_PROMPT


def build_question_chain(llm: ChatOpenAI):
    return QUESTION_PROMPT | llm | StrOutputParser()
