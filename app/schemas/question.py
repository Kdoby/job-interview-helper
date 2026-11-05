from app.schemas.base import CamelModel


class AiQuestionResponse(CamelModel):
    question: str
