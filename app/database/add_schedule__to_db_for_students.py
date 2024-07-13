import os
from app.database.models import async_session
from app.database.models import User, Teacher, Student, ScheduleForStudent
from sqlalchemy import select, update, delete
import aiofiles

async def set_schedule_for_students():
    folder_path = 'schedule/groups'
    files = os.listdir(folder_path)
    async with async_session() as session:
        for file in files:
            if file == 'parse.py':
                continue
            file_path = os.path.join(folder_path, file)
            async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
                group = await f.readline()
                group = group[6:].strip()
                print(group)
                existing_group = await session.scalar(select(ScheduleForStudent).filter(ScheduleForStudent.group == group.strip()))
                schedule = None
                if not existing_group:
                    schedule = ScheduleForStudent(group=group.strip())
                    session.add(schedule)
                content = await f.readlines()
                le_cont = len(content)
                i = 1
                current_day = None
                while i != le_cont:
                    current = content[i].strip()
                    if len(current) == 0:
                        i += 1
                        continue
                    elif current in ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']:
                        current_day = current
                        block = ''
                        i += 1
                        while i < le_cont and len(content[i].strip()) != 0:
                            block += content[i]
                            i += 1
                        if current_day == 'Понедельник':
                            if existing_group:
                                mon_schedule = ScheduleForStudent(Monday=block)
                                session.add(mon_schedule)
                        elif current_day == 'Вторник':
                            if existing_group:
                                tue_schedule = ScheduleForStudent(Tuesday=block)
                                session.add(tue_schedule)
                        elif current_day == 'Среда':
                            if existing_group:
                                wed_schedule = ScheduleForStudent(Wednesday=block)
                                session.add(wed_schedule)
                        elif current_day == 'Четверг':
                            if existing_group:
                                thu_schedule = ScheduleForStudent(Thursday=block)
                                session.add(thu_schedule)
                        elif current_day == 'Пятница':
                            if existing_group:
                                fri_schedule = ScheduleForStudent(Friday=block)
                                session.add(fri_schedule)
                        elif current_day == 'Суббота':
                            if existing_group:
                                sat_schedule = ScheduleForStudent(Saturday=block)
                                session.add(sat_schedule)
                    else:import os
from app.database.models import async_session
from app.database.models import User, Teacher, Student, ScheduleForStudent
from sqlalchemy import select, update, delete
import aiofiles

async def set_schedule_for_students():
    folder_path = 'schedule/groups'
    files = os.listdir(folder_path)
    async with async_session() as session:
        for file in files:
            if file == 'parse.py':
                continue
            file_path = os.path.join(folder_path, file)
            async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
                group = await f.readline()
                group = group[6:].strip()
                print(group)
                existing_group = await session.scalar(select(ScheduleForStudent).filter(ScheduleForStudent.group == group))
                schedule = None
                if not existing_group:
                    schedule = ScheduleForStudent(group=group)
                    session.add(schedule)
                content = await f.readlines()
                le_cont = len(content)
                i = 1
                current_day = None
                while i != le_cont:
                    current = content[i].strip()
                    if len(current) == 0:
                        i += 1
                        continue
                    elif current in ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']:
                        current_day = current
                        block = ''
                        i += 1
                        while i < le_cont and len(content[i].strip()) != 0:
                            block += content[i]
                            i += 1
                        if existing_group:
                            if current_day == 'Понедельник':
                                existing_group.Monday = block
                            elif current_day == 'Вторник':
                                existing_group.Tuesday = block
                            elif current_day == 'Среда':
                                existing_group.Wednesday = block
                            elif current_day == 'Четверг':
                                existing_group.Thursday = block
                            elif current_day == 'Пятница':
                                existing_group.Friday = block
                            elif current_day == 'Суббота':
                                existing_group.Saturday = block
                    else:
                        i += 1
        await session.commit()
        print('Commited')
