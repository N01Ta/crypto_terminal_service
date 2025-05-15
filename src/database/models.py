from sqlalchemy import Column, Integer, String, Sequence
from .database import Base  # Импортируем Base из нашего database.py


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    login = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)  # Помним, что пароль пока хранится как есть
    secret_key = Column(String, nullable=False, unique=True,
                        index=True)  # secret_key должен быть уникальным и индексированным

    def __repr__(self):
        return f"<User(id={self.id}, login='{self.login}')>"