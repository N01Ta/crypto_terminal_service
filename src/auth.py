import os
from fastapi import APIRouter, Depends, HTTPException, status, Form
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from typing import Annotated

from database.database import get_db
from database.models import User

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

class UserCreateSchema(BaseModel):
    login: str = Field(..., min_length=3, max_length=50, description="Придумайте логин для терминала")
    password: str = Field(..., min_length=6, description="Придумайте пароль для терминала (минимум 6 символов)")
    mexc_api_key: str = Field(..., description="Ваш API Key от биржи MEXC")
    mexc_api_secret: str = Field(..., description="Ваш API Secret от биржи MEXC")


class UserApiKeysSchema(BaseModel):
    mexc_api_key: str
    mexc_api_secret: str

    class Config:
        from_attributes = True


class LoginResponseSchema(BaseModel):
    login: str
    api_keys: UserApiKeysSchema


async def get_user_by_login(db: AsyncSession, login: str) -> User | None:
    result = await db.execute(select(User).filter(User.login == login))
    return result.scalar_one_or_none()


async def create_db_user(db: AsyncSession, user_data: UserCreateSchema) -> User:
    db_user = User(
        login=user_data.login,
        password=user_data.password,  # Пароль для нашего сервиса
        mexc_api_key=user_data.mexc_api_key,
        mexc_api_secret=user_data.mexc_api_secret  # API биржи
    )
    db.add(db_user)
    try:
        await db.commit()
        await db.refresh(db_user)
    except IntegrityError:  # Обработка случая, если логин для нашего сервиса уже существует
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Login for the service already registered."
        )
    return db_user


# --- Эндпоинты ---

@router.post("/register", response_model=LoginResponseSchema,
             status_code=status.HTTP_201_CREATED)  # Возвращаем сразу как при логине
async def register_user(user_data: UserCreateSchema, db: AsyncSession = Depends(get_db)):
    """
    Регистрация нового пользователя в терминале и привязка его MEXC API ключей.
    - login логин для доступа к терминалу.
    - password пароль для доступа к терминалу.
    - mexc_api_key API Key от биржи MEXC.
    - mexc_api_secret API Secret от биржи MEXC.
    Возвращает логин пользователя и его API ключи для немедленного использования.
    """
    existing_user = await get_user_by_login(db, login=user_data.login)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This login is already taken for the terminal."
        )

    # Тут можно добавить проверку на уникальность пары mexc_api_key, если это важно,
    # но обычно один API ключ может использоваться только одним пользователем системы.
    # Однако, если разные пользователи системы могут случайно ввести один и тот же API ключ,
    # это может быть проблемой. Пока для простоты опустим.

    created_user = await create_db_user(db, user_data)

    return LoginResponseSchema(
        login=created_user.login,
        api_keys=UserApiKeysSchema(
            mexc_api_key=created_user.mexc_api_key,
            mexc_api_secret=created_user.mexc_api_secret
        )
    )


@router.post("/login", response_model=LoginResponseSchema)
async def login_user(
        login: Annotated[str, Form()],  # Логин для нашего сервиса
        password: Annotated[str, Form()],  # Пароль для нашего сервиса
        db: AsyncSession = Depends(get_db)
):
    """
    Аутентификация пользователя в терминале.
    Принимает `login` и `password` (для терминала) в виде form-data.
    Возвращает логин пользователя и его привязанные MEXC API ключи.
    """
    user = await get_user_by_login(db, login=login)

    # Проверяем, что пользователь существует и пароль для нашего сервиса совпадает
    if not user or not (user.password == password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect terminal login or password",
        )

    # Проверяем, что у пользователя есть привязанные ключи
    if not user.mexc_api_key or not user.mexc_api_secret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MEXC API keys not found for this user. Please register them or contact support.",
        )

    return LoginResponseSchema(
        login=user.login,
        api_keys=UserApiKeysSchema(
            mexc_api_key=user.mexc_api_key,
            mexc_api_secret=user.mexc_api_secret
        )
    )