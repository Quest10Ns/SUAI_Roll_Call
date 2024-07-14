import os
from app.database.models import async_session
from app.database.models import User, Teacher, Student, ScheduleForStudent, ScheduleForTeacher
from sqlalchemy import select, update, delete
import aiofiles


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


async def get_schedule(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        if user.status == 'Студент':
            student = await session.scalar(select(Student).filter(Student.user_id == user.id))
            if student:
                schedule = await session.scalar(
                    select(ScheduleForStudent).filter(ScheduleForStudent.group == student.group))
                return schedule
        else:
            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == user.id))
            if teacher:
                Initials = teacher.initials.split(' ')
                FIO = f'{Initials[0]} {Initials[1][0]}.{Initials[2][0]}.'
                schedule = await session.scalar(select(ScheduleForTeacher).filter(ScheduleForTeacher.Teacher == FIO))
                return schedule

async def get_right_gpoup(student_group):
    async with async_session() as session:
        group = await session.scalar(select(ScheduleForStudent).filter(ScheduleForStudent.group == student_group))
        return bool(group)

async def get_right_initials(teacher_initials):
    async with async_session() as session:
        teacher_initials = teacher_initials.split()
        result = ''
        for i in range(len(teacher_initials)):
            if i == 0:
                result += teacher_initials[i] + ' '
            else:
                result += teacher_initials[i][0] + '.'

        initials = await session.scalar(select(ScheduleForTeacher).filter(ScheduleForTeacher.Teacher == result))
        return bool(initials)

