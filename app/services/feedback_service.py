from app.clients.llm_client import LlmClient
from app.core.exceptions import AnswerNotFoundError
from app.domain.answer import Answer
from app.repositories.answer_repository import AnswerRepository
from app.schemas.feedback import AiFeedbackResponse


INSTRUCTIONS = (
    "너는 IT 회사의 20년차 개발자이고, 현재 면접관으로 참석했다. 사용자의 질문에 대한 답을 보고 적절한 피드백을 준다."
    "score는 0~100점 사이로 주고, 피드백은 1000자 이하의 줄글로 준다."
)


class FeedbackService:
    def __init__(self, repository: AnswerRepository, llm_client: LlmClient):
        self.repository = repository
        self.llm_client = llm_client

    # 1. 답변 조회
    def find_answer(self, answer_id: int) -> Answer:
        answer = self.repository.find_by_id(answer_id)

        if answer is None:
            raise AnswerNotFoundError(answer_id)

        return answer

    # 2. 프롬프트 생성
    def create_prompt(self, answer: Answer) -> str:
        return f"""
            면접 질문: {answer.question}
            지원자 답변: {answer.answer}
            자신감: {answer.confidence}
        """

    # 3. LLM 호출
    async def create_feedback(self, answer_id: int) -> AiFeedbackResponse:
        answer = self.find_answer(answer_id)
        prompt = self.create_prompt(answer)

        return await self.llm_client.ask_structured_async(
            INSTRUCTIONS, prompt, AiFeedbackResponse
        )
