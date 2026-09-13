from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegisterSchema(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        if not any(char.isupper() for char in password):
            raise ValueError(
                "Password must contain at least one uppercase letter."
            )

        if not any(char.islower() for char in password):
            raise ValueError(
                "Password must contain at least one lowercase letter."
            )

        if not any(char.isdigit() for char in password):
            raise ValueError(
                "Password must contain at least one digit."
            )

        if not any(not char.isalnum() for char in password):
            raise ValueError(
                "Password must contain at least one special character."
            )

        return password


class UserResponseSchema(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool

    model_config = {
        "from_attributes": True,
    }


class AccountActivationSchema(BaseModel):
    token: str


class ActivationResendSchema(BaseModel):
    email: EmailStr


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenSchema(BaseModel):
    refresh_token: str


class AccessTokenResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
