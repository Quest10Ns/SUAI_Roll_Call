import os

from sqlalchemy import BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from dotenv import load_dotenv

load_dotenv()
engine = create_async_engine(url= os.getenv('SQLALCHEMY_URL'))

async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'Users'

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id = mapped_column(BigInteger)
    status = mapped_column(String(15), nullable=True)
    # initials = mapped_column(String(150),nullable=True)
    # group_or_department = mapped_column(String(7), nullable=True)

class Teacher(Base):
    __tablename__ = 'Teachers'

    id: Mapped[int] = mapped_column(primary_key=True)
    initials = mapped_column(String(150), unique=True, nullable=True)  # уникальность фио студента
    department = mapped_column(String(4), nullable=True)
    user_id = mapped_column(ForeignKey('Users.id'))

class Student(Base):
    __tablename__ = 'Students'

    id: Mapped[int] = mapped_column(primary_key=True)
    initials = mapped_column(String(150), unique=True, nullable=True)  # уникальность фио студента
    group = mapped_column(String(13), nullable=True)
    user_id = mapped_column(ForeignKey('Users.id'))


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
