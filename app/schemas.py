from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from uuid import UUID

# Format E.164 : "+" optionnel puis 8 à 15 chiffres (ex. +237690000000)
PHONE_PATTERN = r"^\+?[0-9]{8,15}$"


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(pattern=PHONE_PATTERN)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
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
