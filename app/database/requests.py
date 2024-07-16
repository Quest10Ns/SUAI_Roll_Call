import os
from app.database.models import async_session
from app.database.models import User, Teacher, Student, ScheduleForStudent, ScheduleForTeacher, MainScheduleForTeacher, \
    ListOfPresent
from sqlalchemy import select, update, delete
from datetime import datetime, time, date
import time as tim
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
        today1 = date.fromtimestamp(tim.time())
        current_week = (date(today1.year, today1.month, today1.day).isocalendar()[1]) % 2
        now = datetime.now().time()
        start_timeFirst = time(9, 15)
        end_timeFirst = time(10, 0)
        start_timeSecond = time(22, 10)
        end_timeSecond = time(23, 50)
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
                if current_week == 1:
                    pattern_lesson = r"1 пара \(9:30–11:00\) [ПРЛ]+.*? – (.*) – |1 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|1 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_gruoup = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_gruoup, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"1 пара \(9:30–11:00\) [ПРЛ]+.*? – (.*) – |1 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_gruoup = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_gruoup, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern_lesson = r"2 пара \(11:10–12:40\) [ПРЛ]+.*? – (.*) – |2 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|2 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"2 пара \(11:10–12:40\) [ПРЛ]+.*? – (.*) – |2 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern_lesson = r"3 пара \(13:00–14:30\) [ПРЛ]+.*? – (.*) – |3 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|3 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"3 пара \(13:00–14:30\) [ПРЛ]+.*? – (.*) – |3 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern_lesson = r"4 пара \(15:00–16:30\) [ПРЛ]+.*? – (.*) – |4 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|4 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"4 пара \(15:00–16:30\) [ПРЛ]+.*? – (.*) – |4 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern_lesson = r"5 пара \(16:40–18:10\) [ПРЛ]+.*? – (.*) – |5 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|5 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"5 пара \(16:40–18:10\) [ПРЛ]+.*? – (.*) – |5 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern_lesson = r"6 пара \(18:30–20:00\) [ПРЛ]+.*? – (.*) – |6 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|6 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"6 пара \(18:30–20:00\) [ПРЛ]+.*? – (.*) – |6 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern_lesson = r"7 пара \(20:10–21:40\) [ПРЛ]+.*? – (.*) – |7 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|7 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"7 пара \(20:10–21:40\) [ПРЛ]+.*? – (.*) – |7 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
        elif today == 1:
            schedule_string = mainSchedule.Tuesday
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern_lesson = r"1 пара \(9:30–11:00\) [ПРЛ]+.*? – (.*) – |1 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|1 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_gruoup = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_gruoup, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"1 пара \(9:30–11:00\) [ПРЛ]+.*? – (.*) – |1 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_gruoup = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_gruoup, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern_lesson = r"2 пара \(11:10–12:40\) [ПРЛ]+.*? – (.*) – |2 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|2 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"2 пара \(11:10–12:40\) [ПРЛ]+.*? – (.*) – |2 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern_lesson = r"3 пара \(13:00–14:30\) [ПРЛ]+.*? – (.*) – |3 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|3 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"3 пара \(13:00–14:30\) [ПРЛ]+.*? – (.*) – |3 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern_lesson = r"4 пара \(15:00–16:30\) [ПРЛ]+.*? – (.*) – |4 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|4 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"4 пара \(15:00–16:30\) [ПРЛ]+.*? – (.*) – |4 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern_lesson = r"5 пара \(16:40–18:10\) [ПРЛ]+.*? – (.*) – |5 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|5 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"5 пара \(16:40–18:10\) [ПРЛ]+.*? – (.*) – |5 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern_lesson = r"6 пара \(18:30–20:00\) [ПРЛ]+.*? – (.*) – |6 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|6 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"6 пара \(18:30–20:00\) [ПРЛ]+.*? – (.*) – |6 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern_lesson = r"7 пара \(20:10–21:40\) [ПРЛ]+.*? – (.*) – |7 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|7 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"7 пара \(20:10–21:40\) [ПРЛ]+.*? – (.*) – |7 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
        elif today == 2:
            schedule_string = mainSchedule.Wednesday
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern_lesson = r"1 пара \(9:30–11:00\) [ПРЛ]+.*? – (.*) – |1 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|1 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_gruoup = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_gruoup, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"1 пара \(9:30–11:00\) [ПРЛ]+.*? – (.*) – |1 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_gruoup = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_gruoup, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern_lesson = r"2 пара \(11:10–12:40\) [ПРЛ]+.*? – (.*) – |2 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|2 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"2 пара \(11:10–12:40\) [ПРЛ]+.*? – (.*) – |2 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern_lesson = r"3 пара \(13:00–14:30\) [ПРЛ]+.*? – (.*) – |3 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|3 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"3 пара \(13:00–14:30\) [ПРЛ]+.*? – (.*) – |3 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern_lesson = r"4 пара \(15:00–16:30\) [ПРЛ]+.*? – (.*) – |4 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|4 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"4 пара \(15:00–16:30\) [ПРЛ]+.*? – (.*) – |4 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern_lesson = r"5 пара \(16:40–18:10\) [ПРЛ]+.*? – (.*) – |5 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|5 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"5 пара \(16:40–18:10\) [ПРЛ]+.*? – (.*) – |5 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern_lesson = r"6 пара \(18:30–20:00\) [ПРЛ]+.*? – (.*) – |6 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|6 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"6 пара \(18:30–20:00\) [ПРЛ]+.*? – (.*) – |6 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern_lesson = r"7 пара \(20:10–21:40\) [ПРЛ]+.*? – (.*) – |7 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|7 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"7 пара \(20:10–21:40\) [ПРЛ]+.*? – (.*) – |7 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
        elif today == 3:
            schedule_string = mainSchedule.Thursday
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern_lesson = r"1 пара \(9:30–11:00\) [ПРЛ]+.*? – (.*) – |1 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|1 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_gruoup = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_gruoup, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"1 пара \(9:30–11:00\) [ПРЛ]+.*? – (.*) – |1 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_gruoup = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_gruoup, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern_lesson = r"2 пара \(11:10–12:40\) [ПРЛ]+.*? – (.*) – |2 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|2 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"2 пара \(11:10–12:40\) [ПРЛ]+.*? – (.*) – |2 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern_lesson = r"3 пара \(13:00–14:30\) [ПРЛ]+.*? – (.*) – |3 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|3 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"3 пара \(13:00–14:30\) [ПРЛ]+.*? – (.*) – |3 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern_lesson = r"4 пара \(15:00–16:30\) [ПРЛ]+.*? – (.*) – |4 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|4 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"4 пара \(15:00–16:30\) [ПРЛ]+.*? – (.*) – |4 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern_lesson = r"5 пара \(16:40–18:10\) [ПРЛ]+.*? – (.*) – |5 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|5 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"5 пара \(16:40–18:10\) [ПРЛ]+.*? – (.*) – |5 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern_lesson = r"6 пара \(18:30–20:00\) [ПРЛ]+.*? – (.*) – |6 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|6 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"6 пара \(18:30–20:00\) [ПРЛ]+.*? – (.*) – |6 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern_lesson = r"7 пара \(20:10–21:40\) [ПРЛ]+.*? – (.*) – |7 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|7 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"7 пара \(20:10–21:40\) [ПРЛ]+.*? – (.*) – |7 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
        elif today == 4:
            schedule_string = mainSchedule.Friday
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern_lesson = r"1 пара \(9:30–11:00\) [ПРЛ]+.*? – (.*) – |1 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|1 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_gruoup = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_gruoup, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"1 пара \(9:30–11:00\) [ПРЛ]+.*? – (.*) – |1 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_gruoup = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_gruoup, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern_lesson = r"2 пара \(11:10–12:40\) [ПРЛ]+.*? – (.*) – |2 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|2 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"2 пара \(11:10–12:40\) [ПРЛ]+.*? – (.*) – |2 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern_lesson = r"3 пара \(13:00–14:30\) [ПРЛ]+.*? – (.*) – |3 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|3 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"3 пара \(13:00–14:30\) [ПРЛ]+.*? – (.*) – |3 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern_lesson = r"4 пара \(15:00–16:30\) [ПРЛ]+.*? – (.*) – |4 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|4 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"4 пара \(15:00–16:30\) [ПРЛ]+.*? – (.*) – |4 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern_lesson = r"5 пара \(16:40–18:10\) [ПРЛ]+.*? – (.*) – |5 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|5 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"5 пара \(16:40–18:10\) [ПРЛ]+.*? – (.*) – |5 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern_lesson = r"6 пара \(18:30–20:00\) [ПРЛ]+.*? – (.*) – |6 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|6 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"6 пара \(18:30–20:00\) [ПРЛ]+.*? – (.*) – |6 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern_lesson = r"7 пара \(20:10–21:40\) [ПРЛ]+.*? – (.*) – |7 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|7 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"7 пара \(20:10–21:40\) [ПРЛ]+.*? – (.*) – |7 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
        elif today == 5:
            schedule_string = mainSchedule.Saturday
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern_lesson = r"1 пара \(9:30–11:00\) [ПРЛ]+.*? – (.*) – |1 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|1 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_gruoup = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_gruoup, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"1 пара \(9:30–11:00\) [ПРЛ]+.*? – (.*) – |1 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_gruoup = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_gruoup, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern_lesson = r"2 пара \(11:10–12:40\) [ПРЛ]+.*? – (.*) – |2 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|2 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"2 пара \(11:10–12:40\) [ПРЛ]+.*? – (.*) – |2 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern_lesson = r"3 пара \(13:00–14:30\) [ПРЛ]+.*? – (.*) – |3 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|3 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"3 пара \(13:00–14:30\) [ПРЛ]+.*? – (.*) – |3 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern_lesson = r"4 пара \(15:00–16:30\) [ПРЛ]+.*? – (.*) – |4 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|4 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"4 пара \(15:00–16:30\) [ПРЛ]+.*? – (.*) – |4 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern_lesson = r"5 пара \(16:40–18:10\) [ПРЛ]+.*? – (.*) – |5 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|5 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"5 пара \(16:40–18:10\) [ПРЛ]+.*? – (.*) – |5 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern_lesson = r"6 пара \(18:30–20:00\) [ПРЛ]+.*? – (.*) – |6 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|6 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"6 пара \(18:30–20:00\) [ПРЛ]+.*? – (.*) – |6 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern_lesson = r"7 пара \(20:10–21:40\) [ПРЛ]+.*? – (.*) – |7 пара .* ▲ [ПРЛ]+ – (.*) – .* ▼|7 пара .* ▲ [ПРЛ]+ – (.*) –"
                    pattern_group = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                else:
                    pattern_lesson = r"7 пара \(20:10–21:40\) [ПРЛ]+.*? – (.*) – |7 пара .* ▼ [ПРЛ]+ – (.*) –"
                    pattern_group = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern_lesson, schedule_string)
                    result1 = []
                    for i in range(len(matches1)):
                        for j in range(len(matches1[i])):
                            if matches1[i][j] != '':
                                result1.append(matches1[i][j])
                    result2 = []
                    matches2 = re.findall(pattern_group, schedule_string)
                    for i in range(len(matches2[0])):
                        if len(matches2[0][i]) > 0:
                            result2.append((matches2[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result2)):
                        for j in range(len(result2[i])):
                            if result2[i][j] not in groups and result2[i][j] != '':
                                groups.append(result2[i][j])
                matches = result1
                groups = ' '.join(groups)
        list_of_present = ListOfPresent(Teacher=teacher.initials, Pair = matches[0], group = groups ,code = code, status = 'open', teacher_id=teacher.id)
        session.add(list_of_present)
        await session.commit()
