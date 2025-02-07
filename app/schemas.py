"""
Схемы Pydantic для валидации данных API.
"""

from pydantic import BaseModel, AnyUrl


class ServerBase(BaseModel):
    """Базовая схема сервера."""
    name: str
    url: AnyUrl


class ServerCreate(ServerBase):
    """Схема для создания сервера."""
    pass


class ServerResponse(ServerBase):
    """Схема ответа с данными сервера."""
    id: int

    class Config:
        """Настройки Pydantic для работы с ORM."""
        orm_mode = True


class FileResponse(BaseModel):
    """Схема ответа с данными о файле."""
    id: int
    name: str
    status: str
    server_id: int

    class Config:
        """Настройки Pydantic для работы с ORM."""
        orm_mode = True
