"""
Маршруты FastAPI для работы с серверами и файлами.

- `POST /servers/` — создание сервера.
- `GET /servers/{server_id}/files/` — получение списка файлов сервера.
- `POST /servers/{server_id}/files/download` — запуск задачи скачивания файлов.
"""

from fastapi import Depends, HTTPException, APIRouter

from app.database_conf import SessionLocal, get_db
from app.models import Server, File
from app.schemas import ServerResponse, ServerCreate, FileResponse
from app.tasks import celery_app

router = APIRouter()

@router.post("/servers/", response_model=ServerResponse)
def create_server(server: ServerCreate, db: SessionLocal = Depends(get_db)):
    """
    Создает новый сервер.
    """
    db_server = Server(name=server.name, url=str(server.url))
    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    return db_server

@router.get(
    "/servers/{server_id}/files/",
    response_model=list[FileResponse]
)
def list_files(server_id: int, db: SessionLocal = Depends(get_db)):
    """
    Получает список файлов на сервере.
    """
    files = db.query(File).filter(File.server_id == server_id).all()
    return files

@router.post("/servers/{server_id}/files/download")
def trigger_file_download(server_id: int, db: SessionLocal = Depends(get_db)):
    """Запускает процесс скачивания файлов с сервера."""
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    celery_app.send_task(
        "app.tasks.download_files",
        args=[server.id, server.url]
    )
    return {"message": "File download triggered"}