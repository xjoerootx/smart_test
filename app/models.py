"""
Модели базы данных для хранения информации о серверах и файлах.
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database_conf import Base


class Server(Base):
    """ Модель сервера SFTP."""
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    url = Column(String, nullable=False)
    files = relationship("File", back_populates="server")


class File(Base):
    """ Модель загружаемого файла."""
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    status = Column(String, default="pending")
    server_id = Column(Integer, ForeignKey("servers.id"))
    server = relationship("Server", back_populates="files")
