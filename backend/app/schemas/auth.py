from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserPublic(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    user: UserPublic


class CreateAccountRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole


class InvitationConsumeRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class PasswordResetConsumeRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class GenericMessageResponse(BaseModel):
    message: str


class InvitationIssuedResponse(BaseModel):
    activation_token: str


class PasswordResetIssuedResponse(BaseModel):
    reset_token: str
