from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    login: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: dict


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(created|confirmed|processing|shipped|delivered|cancelled)$")
