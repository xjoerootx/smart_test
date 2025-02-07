Поднимаем контейнеры:
```sudo docker compose up```

Создаем файл для загрузки, например 1ГБ
```sudo fallocate -l 1G sftp_data/bigfile_1GB.bin```

открываем Swagger по адресу:
```http://0.0.0.0:8000/docs```

и в ручке POST /servers/ отправляем запрос:
```
{
  "name": "test",
  "url": "sftp://joeroot:password@sftp:22/upload"
}
```

После проверки на наличие новых файлов (1минута) начнется загрузка