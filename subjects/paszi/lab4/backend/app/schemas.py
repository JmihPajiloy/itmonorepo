import re
import string

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Credentials(StrictModel):
    login: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    password: SecretStr = Field(min_length=8, max_length=128)


class Registration(Credentials):
    @field_validator("password")
    @classmethod
    def strong_password(cls, secret: SecretStr) -> SecretStr:
        value = secret.get_secret_value()
        if not (all(re.search(pattern, value) for pattern in (r"[A-Z]", r"[a-z]", r"[0-9]"))
                and any(char in string.punctuation for char in value)):
            raise ValueError("Пароль должен содержать заглавную и строчную латинские буквы, цифру и специальный символ")
        return secret


class ResourceInput(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=10000)

    @field_validator("title", "content")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Поле не может состоять из пробелов")
        return value


class PermissionInput(StrictModel):
    can_read: bool = False
    can_update: bool = False
    can_delete: bool = False
