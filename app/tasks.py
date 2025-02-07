"""
Фоновая обработка задач с Celery.
"""

import logging
from datetime import datetime, timezone
import aiofiles
import asyncssh
from celery import Celery
from celery.schedules import crontab
from app.database_conf import SessionLocal
from app.minio_conf import minio_client, BUCKET_NAME
from app.models import File, Server
from app.event_producer import EventProducer

# Инициализация Celery
celery_app = Celery(
    main='app.tasks',
    broker='amqp://guest:guest@rabbitmq:5672//',
    backend='rpc://'
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Настраиваем периодический запуск мониторинга SFTP"""
    sender.add_periodic_task(crontab(minute="*"), check_for_new_files.s())


@celery_app.task(name="app.tasks.check_for_new_files")
def check_for_new_files():
    """Проверяет новые файлы на всех серверах и запускает их скачивание"""
    db = SessionLocal()
    servers = db.query(Server).all()

    for server in servers:
        logger.info(f"Проверка новых файлов на сервере {server.url}")
        celery_app.send_task(
            name="app.tasks.download_files",
            args=[server.id, server.url]
        )

    db.close()


@celery_app.task(name='app.tasks.download_files')
def download_files(server_id, server_url):
    """Запускает асинхронное скачивание файлов"""
    import asyncio
    asyncio.run(download_files_async(server_id, server_url))


async def download_files_async(server_id, server_url):
    """Асинхронное скачивание файлов с SFTP и загрузка в MinIO."""
    try:
        logger.info(f"Подключение к серверу {server_url}")
        async with asyncssh.connect(
            host='sftp',
            port=22,
            username='joeroot',
            password='password',
            known_hosts=None
        ) as conn:
            async with conn.start_sftp_client() as sftp:
                files = await sftp.listdir('/upload')
                logger.info(f"Найдено файлов: {len(files)}")

                db = SessionLocal()

                for filename in files:
                    if filename in ["..", "."]:
                        logger.warning(
                            f"Пропускаем подозрительный файл: {filename}"
                        )
                        continue

                    # Проверяем, есть ли файл в БД (учитываем статус)
                    existing_file = (
                        db.query(File)
                        .filter(
                            File.name == filename,
                            File.server_id == server_id,
                            File.status.in_(
                                ["uploaded", "downloading"]
                            )
                        )
                        .first()
                    )
                    if existing_file:
                        logger.info(
                            f"Файл {filename} уже в обработке или загружен, "
                            "пропускаем."
                        )
                        continue

                    remote_path = f"/upload/{filename}"
                    local_path = f"/tmp/{filename}"

                    # Добавляем файл в БД со статусом "downloading"
                    new_file = File(
                        name=filename,
                        status="downloading",
                        server_id=server_id
                    )
                    db.add(new_file)
                    db.commit()
                    logger.info(
                        f"Файл {filename} помечен как 'downloading' в БД."
                    )
                    logger.info(
                        f"Скачиваем файл: {remote_path} -> {local_path}"
                    )

                    try:
                        async with sftp.open(
                            remote_path,
                            'rb'
                        ) as remote_file, aiofiles.open(
                            file=local_path,
                            mode='wb'
                        ) as local_file:
                            data = await remote_file.read()
                            await local_file.write(data)
                        logger.info(
                            f"Файл {filename} успешно скачан."
                        )
                    except Exception as e:
                        logger.error(
                            f"Ошибка при скачивании файла {filename}: {e}"
                        )
                        continue

                    # Проверка и загрузка в MinIO
                    try:
                        if not minio_client.bucket_exists(BUCKET_NAME):
                            minio_client.make_bucket(BUCKET_NAME)
                            logger.info(
                                f"Создан бакет MinIO: {BUCKET_NAME}"
                            )
                        logger.info(
                            f"Загрузка файла {filename} в MinIO..."
                        )
                        minio_client.fput_object(
                            BUCKET_NAME,
                            filename,
                            local_path
                        )
                        logger.info(
                            f"Файл {filename} загружен в MinIO."
                        )
                        # После успешной загрузки обновляем статус в БД
                        new_file.status = "uploaded"
                        db.commit()
                        logger.info(
                            f"Файл {filename} помечен как 'uploaded' в БД."
                        )
                    except Exception as e:
                        logger.error(
                            f"Ошибка при загрузке файла {filename} "
                            f"в MinIO: {e}"
                        )
                        # Оставляем статус "downloading" для повторной попытки
                        continue

                    # Отправка уведомления в RabbitMQ
                    try:
                        producer = EventProducer()
                        producer.send_event({
                            "event": "file_uploaded",
                            "file_name": filename,
                            "server_id": server_id,
                            "timestamp": datetime.now(
                                timezone.utc
                            ).isoformat(),
                        })
                        producer.close()
                    except Exception as e:
                        logger.error(
                            f"Ошибка при отправке уведомления в RabbitMQ: {e}"
                        )

                db.close()

    except Exception as e:
        logger.error(
            f"Ошибка подключения к серверу {server_url}: {e}"
        )
