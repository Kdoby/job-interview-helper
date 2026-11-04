from pydantic import Field

from app.schemas.base import CamelModel


class AiFeedbackResponse(CamelModel):
    score: int
    content: str
