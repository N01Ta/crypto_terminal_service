from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv # Для загрузки .env файла
import os

# Версия сервиса (можно вынести в отдельный файл или переменную окружения)
SERVICE_VERSION = os.environ.get("SERVICE_VERSION", "1.2.5")

# Загружаем переменные окружения из .env файла (если он есть)
# Это должно быть в самом начале, до импорта модулей, которые используют os.environ
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
    lifespan=lifespan # Используем lifespan для управления ресурсами при старте/остановке
)

# Подключаем роутер аутентификации
app.include_router(auth_router)

# Новый эндпоинт /sec
@app.get("/sec", tags=["Service Info"])
async def get_service_version():
    """
    Возвращает текущую версию сервиса.
    """
    return {"service_name": "Crypto Terminal Auth Service", "version": SERVICE_VERSION}

# Если вы запускаете этот файл напрямую (например, python src/main.py без uvicorn)
# то этот блок не будет выполнен, так как uvicorn импортирует 'app'.
# Для запуска через uvicorn: uvicorn src.main:app --reload
if __name__ == "__main__":
    import uvicorn
    # Для запуска напрямую, убедитесь, что переменные окружения установлены
    # или .env файл находится в текущей рабочей директории, откуда запускается скрипт.
    # Обычно Uvicorn запускается из корня проекта, где и лежит .env
    uvicorn.run(app, host="0.0.0.0", port=8000)