# main.py (FastAPI сервер)
from fastapi import FastAPI, HTTPException, status, Body
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field # Для модели запроса версии

# Загружаем переменные окружения из .env файла (если он есть)
# Это должно быть сделано до того, как SERVICE_VERSION пытается получить значение из os.environ,
# если SERVICE_VERSION тоже должен быть в .env
load_dotenv() 

# Версия сервиса (эталонная, с которой будет сверяться клиент)
# Может быть жестко задана здесь или также браться из .env
SERVER_EXPECTED_CLIENT_VERSION = os.environ.get("EXPECTED_CLIENT_VERSION", "1.0.3") # Пример версии клиента
# Версия самого API сервера (может быть другой)
API_SERVICE_VERSION = os.environ.get("API_SERVICE_VERSION", "1.2.5") 


# Импорты после load_dotenv, если они зависят от переменных окружения
from database.database import engine, Base 
from auth import router as auth_router 


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"API Service Version: {API_SERVICE_VERSION}")
    print(f"Expected Client Version by Server: {SERVER_EXPECTED_CLIENT_VERSION}")
    print("Starting up FastAPI application...")
    async with engine.begin() as conn:
        # В реальном production лучше использовать Alembic для миграций
        await conn.run_sync(Base.metadata.create_all)
        print("Database tables checked/created.")
    yield
    print("Shutting down FastAPI application...")
    if engine: # Проверяем, что engine не None перед dispose
        await engine.dispose()
        print("Database engine disposed.")


# --- Pydantic модель для запроса проверки версии ---
class ClientVersionInfo(BaseModel):
    client_version: str = Field(..., description="Версия клиентского приложения")


app = FastAPI(
    title="Crypto Terminal Authentication Service",
    description="Сервис авторизации и регистрации для курсового проекта.",
    version=API_SERVICE_VERSION, # Версия самого API сервера
    lifespan=lifespan
)

# Подключаем роутер аутентификации
app.include_router(auth_router)


@app.post("/sec/check_version", tags=["Service Info"])
async def check_client_version(version_info: ClientVersionInfo):
    """
    Принимает версию клиентского приложения и сверяет ее с ожидаемой на сервере.
    - Если версии совпадают, возвращает подтверждение.
    - Если версии не совпадают, возвращает ошибку 426 Upgrade Required.
      (Клиент должен будет обработать этот статус и, например, закрыться или предложить обновление).
    """
    print(f"Received client version check: {version_info.client_version}")
    if version_info.client_version == SERVER_EXPECTED_CLIENT_VERSION:
        return {
            "status": "ok", 
            "message": "Client version is up to date.",
            "server_api_version": API_SERVICE_VERSION 
        }
    else:
        # Статус 426 Upgrade Required - подходящий для этого случая
        raise HTTPException(
            status_code=status.HTTP_426_UPGRADE_REQUIRED,
            detail=f"Client version '{version_info.client_version}' is outdated. Expected version: '{SERVER_EXPECTED_CLIENT_VERSION}'. Please update the application."
        )

@app.get("/sec/info", tags=["Service Info"]) # Оставим GET для получения информации о сервере, если нужно
async def get_server_info():
    """
    Возвращает информацию о сервере, включая версию API и ожидаемую версию клиента.
    """
    return {
        "service_name": "Crypto Terminal Auth Service",
        "api_version": API_SERVICE_VERSION,
        "expected_client_version": SERVER_EXPECTED_CLIENT_VERSION
    }


if __name__ == "__main__":
    import uvicorn
    # Uvicorn будет читать .env файл, если он в той же директории,
    # или если python-dotenv вызван до инициализации uvicorn (что мы и делаем)
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True) # Добавил reload=True для удобства разработки