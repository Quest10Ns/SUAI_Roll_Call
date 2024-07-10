from app.database.models import async_session
from app.database.models import User, Teacher, Student
from sqlalchemy import select, update, delete


async def set_user(tg_id):
    async with  async_session() as session:
        user = await session.scalar(select(User.telegram_id == tg_id))
        if not user:
            session.add(User(telegram_id=tg_id))
            await session.commit()


async def set_user_status(tg_id, status):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        if user:
            user.status = status
            await session.commit()


async def set_student_initials_for_teachers(tg_id, initials):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        if user:
            if user.status == 'Преподаватель':
                teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == user.id))
                if not teacher:
                    session.add(Teacher(initials=initials, user_id=user.id))
                    await session.commit()
                if teacher:
                    teacher.initials = initials
                    await session.commit()


async def set_departmend_for_teachers(tg_id, departmend):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == user.id))
        if user and teacher:
            teacher.department = departmend
            await session.commit()


async def set_student_initials_for_students(tg_id, initials):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        if user:
            if user.status == 'Студент':
                student = await session.scalar(select(Student).filter(Student.user_id == user.id))
                if not student:
                    session.add(Student(initials=initials, user_id=user.id))
                    await session.commit()
                if student:
                    student.initials = initials
                    await session.commit()


async def set_group_for_student(tg_id, group):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        student = await session.scalar(select(Student).filter(Student.user_id == user.id))
        if user and student:
            student.group = group
            await session.commit()

async def get_user_status(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        if user:
            return user.status

async def get_student_initials(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        if user:
            student = await session.scalar(select(Student).filter(Student.user_id == user.id))
            if student:
                return student.initials

async def get_student_group(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        if user:
            student = await session.scalar(select(Student).filter(Student.user_id == user.id))
            if student:
                return student.group


async def get_teachers_initials(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        if user:
            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == user.id))
            if teacher:
                return teacher.initials

async def get_teachers_department(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        if user:
            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == user.id))
            if teacher:
                return teacher.department

async def get_teacher(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        teacher = teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == user.id))
        return teacher

async def get_student(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        student = await session.scalar(select(Student).filter(Student.user_id == user.id))
        return student