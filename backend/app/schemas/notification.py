from datetime import datetime
from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: int
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
