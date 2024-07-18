import os

from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Text, Integer, Date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
engine = create_async_engine(url=os.getenv('SQLALCHEMY_URL'))

async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'Users'

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id = mapped_column(BigInteger)
    status = mapped_column(String(15), nullable=True)


class Teacher(Base):
    __tablename__ = 'Teachers'

    id: Mapped[int] = mapped_column(primary_key=True)
    initials = mapped_column(String(150), nullable=True)
    department = mapped_column(String(4), nullable=True)
    chat_id = mapped_column(BigInteger)
    user_id = mapped_column(ForeignKey('Users.id'))


class Student(Base):
    __tablename__ = 'Students'

    id: Mapped[int] = mapped_column(primary_key=True)
    initials = mapped_column(String(150), nullable=True)
    group = mapped_column(String(13), nullable=True)
    chat_id = mapped_column(BigInteger)
    user_id = mapped_column(ForeignKey('Users.id'))


class ScheduleForStudent(Base):
    __tablename__ = 'ScheduleForStudents'

    id: Mapped[int] = mapped_column(primary_key=True)
    group = mapped_column(String(13), nullable=True)
    Monday = mapped_column(Text, nullable=True)
    Tuesday = mapped_column(Text, nullable=True)
    Wednesday = mapped_column(Text, nullable=True)
    Thursday = mapped_column(Text, nullable=True)
    Friday = mapped_column(Text, nullable=True)
    Saturday = mapped_column(Text, nullable=True)

class ScheduleForTeacher(Base):
    __tablename__ = 'ScheduleForTeachers'

    id: Mapped[int] = mapped_column(primary_key=True)
    Teacher = mapped_column(String(100), nullable=True)
    Monday = mapped_column(Text, nullable=True)
    Tuesday = mapped_column(Text, nullable=True)
    Wednesday = mapped_column(Text, nullable=True)
    Thursday = mapped_column(Text, nullable=True)
    Friday = mapped_column(Text, nullable=True)
    Saturday = mapped_column(Text, nullable=True)

class MainScheduleForTeacher(Base):
    __tablename__ = 'MainScheduleForTeachers'
    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id = mapped_column(ForeignKey('Teachers.id'))
    Monday = mapped_column(Text, nullable=True)
    Tuesday = mapped_column(Text, nullable=True)
    Wednesday = mapped_column(Text, nullable=True)
    Thursday = mapped_column(Text, nullable=True)
    Friday = mapped_column(Text, nullable=True)
    Saturday = mapped_column(Text, nullable=True)

class ListOfPresent(Base):
    __tablename__ = 'ListOfPresents'
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[Date] = mapped_column(Date, default=datetime.now().date())
    Number_pair = mapped_column(Text(6), nullable=True)
    Teacher = mapped_column(String(100), nullable=True)
    Pair = mapped_column(Text, nullable=True)
    group = mapped_column(Text, nullable=True)
    students = mapped_column(Text, nullable=True)
    code = mapped_column(String(15), nullable=True)
    status = mapped_column(String(8), nullable=True)
    teacher_id = mapped_column(ForeignKey('Teachers.id'))


class Rang(Base):
    __tablename__ = 'Rangs'
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id = mapped_column(ForeignKey('Students.id'))
    student_name = mapped_column(String(150), nullable=True)
    mmr = mapped_column(Integer, nullable = True)



async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
