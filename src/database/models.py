from sqlalchemy import Column, Integer, String, Sequence
from .database import Base  # Импортируем Base из нашего database.py


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    login = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    mexc_api_key = Column(String, nullable=False, index=True)
    mexc_api_secret = Column(String, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, login='{self.login}')>"