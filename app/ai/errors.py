import openai
from langchain_core.exceptions import ModelRefusalError
from langchain_core.runnables import Runnable, RunnableConfig

from app.core.exceptions import AiRequestError


def to_ai_request_error(e: openai.OpenAIError) -> AiRequestError:

    # AuthenticationError: OpenAI 서버의 401 응답. API 키가 틀렸거나, 삭제되었거나, 빈 문자열이다.
    if isinstance(e, openai.AuthenticationError):
        return AiRequestError(
            "OpenAI API 키가 올바르지 않습니다. OPENAI_API_KEY를 확인하세요."
        )

    # RateLimitError: OpenAI 서버의 429 응답. 짧은 시간에 요청을 너무 많이 보냈거나, 계정의 충전 잔액이 바닥났다.
    if isinstance(e, openai.RateLimitError):
        return AiRequestError("OpenAI 요청 한도를 넘었거나 충전 잔액이 부족합니다.")

    # APITimeoutError: 요청은 보냈지만 timeout(OPENAI_TIMEOUT_SECONDS) 안에 응답이 오지 않음.
    # APITimeoutError는 APIConnectionError의 자식 클래스라서 예외 계층 구조상 먼저 검사한다.
    if isinstance(e, openai.APITimeoutError):
        return AiRequestError("OpenAI 응답이 제한 시간 안에 오지 않았습니다.")

    # APIConnectionError: OpenAI 서버에 닿지 못함. 인터넷 연결이 끊겼거나, 방화벽·프록시가 막았다.
    # (응답 자체를 받지 못했으므로 HTTP 상태 코드가 없다)
    if isinstance(e, openai.APIConnectionError):
        return AiRequestError("OpenAI 서버에 연결할 수 없습니다.")

    # 그 밖의 오류: 400(요청 형식 오류, 없는 모델 이름 등), 403(권한 없음), 500번대(OpenAI 서버 오류) 등.
    # 메시지에 원래 예외의 내용을 함께 담는다.
    return AiRequestError(f"OpenAI 호출 실패 : {e}")


async def ainvoke_or_raise(
    runnable: Runnable, input: dict, config: RunnableConfig | None = None
):
    try:
        result = await runnable.ainvoke(input, config)
    except openai.OpenAIError as e:
        raise to_ai_request_error(e) from e
    except (ValueError, ModelRefusalError) as e:
        raise AiRequestError("구조화된 응답을 받지 못했습니다.") from e
    return result


def invoke_or_raise(
    runnable: Runnable, input: dict, config: RunnableConfig | None = None
):
    try:
        result = runnable.invoke(input, config)
    except openai.OpenAIError as e:
        raise to_ai_request_error(e) from e
    except (ValueError, ModelRefusalError) as e:
        raise AiRequestError("구조화된 응답을 받지 못했습니다.") from e
    return result
