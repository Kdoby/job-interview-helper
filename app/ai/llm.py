from langchain_openai import ChatOpenAI
from app.core.config import Settings


def build_chat_model(settings: Settings) -> ChatOpenAI:

    if settings.openai_api_key is None:
        raise ValueError("OPENAI_API_KEY가 없어 OpenAI 클라이언트를 만들 수 없습니다.")

    # 모델명
    model = settings.openai_model
    # 추론 정도
    reasoning = settings.openai_reasoning_effort
    # API 키값 준비
    api_key = settings.openai_api_key.get_secret_value()
    # timeout
    timeout = settings.openai_timeout_seconds
    # output tokens
    max_output_tokens = settings.openai_max_output_tokens

    llm = ChatOpenAI(
        model=model,
        reasoning={"effort": reasoning},
        api_key=api_key,
        timeout=timeout,
        max_tokens=max_output_tokens,
        max_retries=1,
        store=False,
    )

    return llm
