from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

# Версия сервиса
SERVICE_VERSION = os.environ.get("SERVICE_VERSION", "1.2.5")

# Загружаем переменные окружения из .env файла (если он есть)
load_dotenv()

from database.database import engine, Base # Импортируем engine и Base из нашего database.py
from auth import router as auth_router # Импортируем роутер аутентификации



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, который выполнится перед запуском приложения
    print("Starting up...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Database tables checked/created.")
    yield
    # Код, который выполнится после остановки приложения
    print("Shutting down...")
    await engine.dispose() # капитально закрываем пул соединений


app = FastAPI(
    title="Crypto Terminal Authentication Service",
    description="Сервис авторизации и регистрации для курсового проекта.",
    version=SERVICE_VERSION,
    lifespan=lifespan
)


app.include_router(auth_router)


@app.get("/sec", tags=["Service Info"])
async def get_service_version():
    """
    Возвращает текущую версию сервиса.
    """
    return {"service_name": "Crypto Terminal Auth Service", "version": SERVICE_VERSION}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)