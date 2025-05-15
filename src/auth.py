import os
from fastapi import APIRouter, Depends, HTTPException, status, Form  # Form для явного приема form-data
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from typing import Annotated  # Для FastAPI >= 0.95.0

from database.database import get_db
from database.models import User

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


class UserCreateSchema(BaseModel):
    login: str = Field(..., min_length=3, max_length=50, description="Уникальный логин пользователя")
    password: str = Field(..., min_length=6, description="Пароль пользователя (минимум 6 символов)")
    secret_key: str = Field(..., min_length=10, description="Секретный ключ пользователя (минимум 10 символов)")


class UserInfoSchema(BaseModel):
    login: str
    secret_key: str

    class Config:
        from_attributes = True


async def get_user_by_login(db: AsyncSession, login: str) -> User | None:
    result = await db.execute(select(User).filter(User.login == login))
    return result.scalar_one_or_none()


async def create_db_user(db: AsyncSession, user_data: UserCreateSchema) -> User:
    db_user = User(
        login=user_data.login,
        password=user_data.password,  # Пароль хранится как есть
        secret_key=user_data.secret_key
    )
    db.add(db_user)
    try:
        await db.commit()
        await db.refresh(db_user)
    except IntegrityError:
        await db.rollback()
        existing_user_by_login = await get_user_by_login(db, user_data.login)
        if existing_user_by_login:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Login already registered."
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Secret key already in use or another integrity constraint violated."
        )
    return db_user


@router.post("/register", response_model=UserInfoSchema, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreateSchema, db: AsyncSession = Depends(get_db)):
    """
    Регистрация нового пользователя.
    - **login**: уникальный логин пользователя.
    - **password**: пароль.
    - **secret_key**: персональный секретный ключ.
    Возвращает информацию о созданном пользователе.
    """
    existing_user = await get_user_by_login(db, login=user_data.login)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Login already registered."
        )

    result = await db.execute(select(User).filter(User.secret_key == user_data.secret_key))
    existing_secret_key = result.scalar_one_or_none()
    if existing_secret_key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This secret key is already in use."
        )

    created_user = await create_db_user(db, user_data)
    return UserInfoSchema(login=created_user.login, secret_key=created_user.secret_key)


@router.post("/login", response_model=UserInfoSchema)  # Раньше был /token
async def login_user(
        login: Annotated[str, Form()],
        password: Annotated[str, Form()],
        db: AsyncSession = Depends(get_db)
):
    """
    Аутентификация пользователя.
    Принимает `login` и `password` в виде form-data.
    Возвращает информацию о пользователе (`login`, `secret_key`) в случае успеха.
    """
    user = await get_user_by_login(db, login=login)
    if not user or not (user.password == password):  # Прямое сравнение паролей
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
            # headers={"WWW-Authenticate": "Bearer"} # Заголовок Bearer не нужен без JWT
        )

    return UserInfoSchema(login=user.login, secret_key=user.secret_key)