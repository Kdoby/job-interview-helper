import time

from langchain_core.callbacks.base import BaseCallbackHandler


class TokenUsageTracker(BaseCallbackHandler):
    def __init__(self):
        # 입력, 출력, 총합 토큰 및 호출 횟수 누적 변수를 초기화한다.
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.calls = 0
        self.start = time.perf_counter()
        self.model = None

    # 각 LLM 호출이 완료될 때마다 usage_metadata를 파싱해 누적한다.
    def on_llm_end(self, response, **kwargs):

        self.calls += 1
        for generations in response.generations:
            for gen in generations:
                self.model = gen.message.response_metadata.get("model_name")
                usage = getattr(gen.message, "usage_metadata", None)
                if usage:
                    self.input_tokens += usage.get("input_tokens", 0)
                    self.output_tokens += usage.get("output_tokens", 0)
                    self.total_tokens += usage.get("total_tokens", 0)

    def print_usage(self, label: str) -> None:

        if self.calls == 0:
            return

        elapsed_ms = int((time.perf_counter() - self.start) * 1000)

        print(
            f"[{label}] model={self.model}, 입력 토큰={self.input_tokens}, 출력 토큰={self.output_tokens}, {elapsed_ms}ms"
        )
