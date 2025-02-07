Поднимаем контейнеры:
```sudo docker compose up```

открываем Swagger по адресу:
```http://0.0.0.0:8000/docs```

и в ручке POST /servers/ отправляем запрос:
```
{
  "name": "test",
  "url": "sftp://joeroot:password@sftp:22/upload"
}
```

После этого начинается автоматическая загрузка файла