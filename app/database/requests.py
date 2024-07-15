import os
from app.database.models import async_session
from app.database.models import User, Teacher, Student, ScheduleForStudent, ScheduleForTeacher, MainScheduleForTeacher, \
    ListOfPresent
from sqlalchemy import select, update, delete
from datetime import datetime, time
import aiofiles
import re


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


async def set_student_initials_for_teachers(tg_id, chat_id, initials):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        if user:
            if user.status == 'Преподаватель':
                teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == user.id))
                if not teacher:
                    session.add(Teacher(initials=initials, user_id=user.id, chat_id=chat_id))
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


async def set_student_initials_for_students(tg_id, chat_id, initials):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        if user:
            if user.status == 'Студент':
                student = await session.scalar(select(Student).filter(Student.user_id == user.id))
                if not student:
                    session.add(Student(initials=initials, chat_id=chat_id, user_id=user.id))
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


async def set_schedule_for_certain_teacher(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == user.id))
        if teacher:
            Initials = teacher.initials.split(' ')
            FIO = f'{Initials[0]} {Initials[1][0]}.{Initials[2][0]}.'
            schedule = await session.scalar(select(ScheduleForTeacher).filter(ScheduleForTeacher.Teacher == FIO))
            if schedule:
                mainSchedule = await session.scalar(
                    select(MainScheduleForTeacher).filter(MainScheduleForTeacher.teacher_id == teacher.id))
                if not mainSchedule:
                    session.add(
                        MainScheduleForTeacher(teacher_id=teacher.id, Monday=schedule.Monday, Tuesday=schedule.Tuesday,
                                               Wednesday=schedule.Wednesday, Thursday=schedule.Thursday,
                                               Friday=schedule.Friday, Saturday=schedule.Saturday))
                    await session.commit()


async def get_schedule_for_certain_teacher(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == user.id))
        if teacher:
            Initials = teacher.initials.split(' ')
            FIO = f'{Initials[0]} {Initials[1][0]}.{Initials[2][0]}.'
            schedule = await session.scalar(select(ScheduleForTeacher).filter(ScheduleForTeacher.Teacher == FIO))
            if schedule:
                mainSchedule = await session.scalar(
                    select(MainScheduleForTeacher).filter(MainScheduleForTeacher.teacher_id == teacher.id))
                if mainSchedule:
                    return mainSchedule


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


async def set_data_for_listOfPresent(tg_id, code):
    async with async_session() as session:
        user = await session.scalar(select(User).filter(User.telegram_id == tg_id))
        teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == user.id))
        mainSchedule = await session.scalar(select(MainScheduleForTeacher).filter(MainScheduleForTeacher.teacher_id == teacher.id))
        today = datetime.now().weekday()
        now = datetime.now().time()
        start_timeFirst = time(9, 15)
        end_timeFirst = time(10, 0)
        start_timeSecond = time(10, 55)
        end_timeSecond = time(11, 20)
        start_timeThird = time(12, 45)
        end_timeThird = time(13, 0)
        start_timeFourth = time(14, 45)
        end_timeFourth = time(15, 0)
        start_timeFifth = time(16, 25)
        end_timeFifth = time(16, 40)
        start_timeSix = time(18, 15)
        end_timeSix = time(18, 30)
        start_timeSeven = time(19, 55)
        end_timeSeven = time(20, 10)
        if today == 0:
            schedule_string = mainSchedule.Monday
            if start_timeFirst <= now <= end_timeFirst:
                pattern = r"1 пара.*?(?=Группа:)"
                patternGruoup = r"1 пара.*?Группа: (\d+[A-ZА-Я]*)"
                matches = re.findall(pattern, schedule_string)
                matchesGroup = re.findall(patternGruoup, schedule_string)
                groups = ', '.join(matchesGroup)
            elif start_timeSecond <= now <= end_timeSecond:
                pattern = r"2 пара.*?(?=Группа:)"
                patternGruoup = r"2 пара.*?Группа: (\d+[A-ZА-Я]*)"
                matches = re.findall(pattern, schedule_string)
                matchesGroup = re.findall(patternGruoup, schedule_string)
                groups = ', '.join(matchesGroup)
            elif start_timeThird <= now <= end_timeThird:
                pattern = r"3 пара.*?(?=Группа:)"
                patternGruoup = r"3 пара.*?Группа: (\d+[A-ZА-Я]*)"
                matches = re.findall(pattern, schedule_string)
                matchesGroup = re.findall(patternGruoup, schedule_string)
                groups = ', '.join(matchesGroup)
            elif start_timeFourth <= now <= end_timeFourth:
                pattern = r"4 пара.*?(?=Группа:)"
                patternGruoup = r"4 пара.*?Группа: (\d+[A-ZА-Я]*)"
                matches = re.findall(pattern, schedule_string)
                matchesGroup = re.findall(patternGruoup, schedule_string)
                groups = ', '.join(matchesGroup)
            elif start_timeFifth <= now <= end_timeFifth:
                pattern = r"5 пара.*?(?=Группа:)"
                patternGruoup = r"5 пара.*?Группа: (\d+[A-ZА-Я]*)"
                matches = re.findall(pattern, schedule_string)
                matchesGroup = re.findall(patternGruoup, schedule_string)
                groups = ', '.join(matchesGroup)
            elif start_timeSix <= now <= end_timeSix:
                pattern = r"6 пара.*?(?=Группа:)"
                patternGruoup = r"6 пара.*?Группа: (\d+[A-ZА-Я]*)"
                matches = re.findall(pattern, schedule_string)
                matchesGroup = re.findall(patternGruoup, schedule_string)
                groups = ', '.join(matchesGroup)
            elif start_timeSeven <= now <= end_timeSeven:
                pattern = r"7 пара.*?(?=Группа:)"
                patternGruoup = r"7 пара.*?Группа: (\d+[A-ZА-Я]*)"
                matches = re.findall(pattern, schedule_string)
                matchesGroup = re.findall(patternGruoup, schedule_string)
                groups = ', '.join(matchesGroup)
        list_of_present = ListOfPresent(Teacher=teacher.initials, Pair = matches[0], group = groups ,code = code, status = 'open', teacher_id=teacher.id)
        session.add(list_of_present)
        await session.commit()
