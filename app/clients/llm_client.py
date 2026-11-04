import asyncio
import time

import openai
from pydantic import BaseModel

from app.core.config import Settings
from app.core.exceptions import AiRequestError


class OpenAiLlmClient:
    def __init__(self, settings: Settings):
        # 전달받은 설정 객체(Settings)를 보관한다
        self.settings = settings
        # 응답 DTO에 담을 모델 이름
        self.model = settings.openai_model

        # 설정 파일로부터 읽어들인 API 키가 없는 경우를 대비해 if문으로 검사한다.
        # 만약 키가 없다면 FastAPI의 lifespan이 이 클래스 대신 FakeLlmClient를 만든다.
        # 그래도 lifespan을 거치지 않고 이 클래스를 직접 만드는 경우(테스트 등)에는 여기서 원인을 알려 주며 멈춘다.
        if settings.openai_api_key is None:
            raise ValueError(
                "OPENAI_API_KEY가 없어 OpenAI 클라이언트를 만들 수 없습니다."
            )
        # API 키값 준비
        api_key = settings.openai_api_key.get_secret_value()

        # 동기 처리용 클라이언트 객체 생성
        self._client = openai.OpenAI(
            api_key=api_key,
            timeout=settings.openai_timeout_seconds,
            max_retries=1,
        )

        # 비동기 처리용 클라이언트 객체 생성
        self._async_client = openai.AsyncOpenAI(
            api_key=api_key,
            timeout=settings.openai_timeout_seconds,
            max_retries=1,
        )

    # 1. 동기 질문:
    # 응답이 올 때까지 이 라인에서 스레드가 멈춰 있다. 따라서 그동안 이 스레드는 다른 일을 하지 못한다.
    def ask(self, instructions: str, question: str) -> str:

        # 요청 시작시간 기록
        start = time.perf_counter()

        # try문 내에서 OpenAI 서버로 요청 전송
        try:
            # OpenAI Responses API 호출 (POST https://api.openai.com/v1/responses)
            response = self._client.responses.create(
                # 사용할 모델
                model=self.settings.openai_model,
                # 지시문(시스템 프롬프트)
                instructions=instructions,
                # 손님의 질문. 문자열 하나를 전달하면 사용자(user)가 보낸 메시지 하나로 처리된다.
                input=question,
                # 출력 토큰 상한
                max_output_tokens=self.settings.openai_max_output_tokens,
                # 추론 정도 (기본값 none : 추론 없이 바로 응답한다)
                reasoning={"effort": self.settings.openai_reasoning_effort},
                # 대화 내용을 OpenAI 서버에 저장하지 않는다
                store=False,
            )
        # openai 라이브러리의 예외(401, 429, 시간 초과 등)를 우리 예외로 바꿔서 다시 던진다.
        # 이때 'from e'를 붙이면 원래 예외가 트레이스백에 함께 찍혀서 원인을 찾기 쉽다.
        except openai.OpenAIError as e:
            raise to_ai_request_error(e) from e

        # 앞서 기록한 시작시간을 전달인자로 하여 콘솔 출력 함수를 호출한다
        print_usage("ask", response, start)

        # OpenAI 서버의 응답 문장을 반환한다
        return response.output_text

    # await 지점에서 이 코루틴은 멈추고, 응답이 오기 전까지 이벤트 루프는 다른 요청을 처리한다.
    async def ask_async(self, instructions: str, question: str) -> str:

        # 요청 시작시간 기록
        start = time.perf_counter()

        # try문 내에서 OpenAI 서버로 요청 전송
        try:
            response = await self._async_client.responses.create(
                model=self.settings.openai_model,
                instructions=instructions,
                input=question,
                max_output_tokens=self.settings.openai_max_output_tokens,
                reasoning={"effort": self.settings.openai_reasoning_effort},
                store=False,
            )
        except openai.OpenAIError as e:
            raise to_ai_request_error(e) from e

        # 앞서 기록한 시작시간을 전달인자로 하여 콘솔 출력 함수를 호출한다
        print_usage("ask_async", response, start)

        # OpenAI 서버의 응답 문장을 반환한다
        return response.output_text

    async def ask_structured_async[T: BaseModel](
        self, instructions: str, question: str, output_type: type[T]
    ) -> T:
        start = time.perf_counter()
        try:
            response = await self._async_client.responses.parse(
                model=self.settings.openai_model,
                instructions=instructions,
                input=question,
                text_format=output_type,
                max_output_tokens=self.settings.openai_max_output_tokens,
                reasoning={"effort": self.settings.openai_reasoning_effort},
                store=False,
            )
        except openai.OpenAIError as e:
            raise to_ai_request_error(e) from e

        print_usage("ask_structured_async", response, start)

        if response.output_parsed is None:
            raise AiRequestError(
                f"구조화된 응답을 받지 못했습니다. (status={response.status})"
            )
        return response.output_parsed

    async def close(self) -> None:
        self._client.close()
        await self._async_client.close()


def print_usage(method: str, response, start: float) -> None:

    # 요청 처리 시간 계산
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    # OpenAI의 응답 객체로부터 토큰 사용량(usage)을 추출.
    usage = response.usage

    if usage is not None:
        print(
            f"[OpenAiLlmClient.{method}] model={response.model}, "
            f"입력 토큰={usage.input_tokens}, 출력 토큰={usage.output_tokens}, {elapsed_ms}ms"
        )


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


class FakeLlmClient:
    def __init__(self, settings: Settings):
        self.delay_seconds = settings.fake_llm_delay_seconds
        self.model = "fake-llm"

    # time.sleep : 이 스레드를 멈춰 세운다. 동기 클라이언트가 응답을 기다리는 것과 같은 상황을 만든다.
    def ask(self, instructions: str, question: str) -> str:
        time.sleep(self.delay_seconds)
        return f"(가짜 응답) '{question}'에 대한 응답입니다. {self.delay_seconds}초 기다렸습니다."

    # await asyncio.sleep : 이 코루틴만 멈춘다. 기다리는 동안 이벤트 루프는 다른 요청을 처리한다.
    # 비동기 클라이언트가 응답을 기다리는 것과 같은 상황을 만든다.
    async def ask_async(self, instructions: str, question: str) -> str:
        await asyncio.sleep(self.delay_seconds)
        return f"(가짜 응답) '{question}'에 대한 응답입니다. {self.delay_seconds}초 기다렸습니다."

    async def ask_structured_async[T: BaseModel](
        self, instructions: str, question: str, output_type: type[T]
    ) -> T:
        await asyncio.sleep(self.delay_seconds)

        return output_type.model_validate(
            {"feedback": "(가짜 응답) 피드백입니다.", "score": 80}
        )

    async def close(self) -> None:
        pass


# 두 클라이언트 중 하나라는 뜻의 타입 이름. 의존성 함수와 AiService의 타입 힌트에 사용한다.
LlmClient = OpenAiLlmClient | FakeLlmClient
