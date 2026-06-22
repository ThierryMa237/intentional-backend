from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID

class UserCreate(BaseModel):
    name: str
    phone: str
    password: str

class UserOut(BaseModel):
    id: UUID
    name: str
    phone: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"