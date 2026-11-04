from pydantic import Field

from app.schemas.base import CamelModel


class AiFeedbackResponse(CamelModel):
    feedback: str
    score: int = Field(ge=0, le=100)
