from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    login: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: dict


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(created|confirmed|processing|shipped|delivered|cancelled)$")


class UserProfileUpdateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=255)
    last_name: str = Field(..., min_length=1, max_length=255)
    middle_name: str | None = Field(None, max_length=255)
    phone: str = Field(..., min_length=5, max_length=255)
    delivery_address: str = Field(..., min_length=5, max_length=500)

    @field_validator("first_name", "last_name", "phone", "delivery_address")
    @classmethod
    def strip_required_value(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Поле не должно быть пустым")
        return value

    @field_validator("middle_name")
    @classmethod
    def strip_middle_name(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None
