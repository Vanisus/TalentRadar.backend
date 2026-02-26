from pydantic import BaseModel, Field


class CandidateTagCreate(BaseModel):
    name: str = Field(..., description="Название тега (например, 'strong JS')")


class CandidateTagRead(BaseModel):
    id: int
    candidate_id: int
    name: str

    class Config:
        from_attributes = True
