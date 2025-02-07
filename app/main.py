"""
Главный файл приложения FastAPI.
"""

from fastapi import FastAPI
from app.endpoints import router

app = FastAPI()

router_list = [
    router
]

for router in router_list:
    app.include_router(router)