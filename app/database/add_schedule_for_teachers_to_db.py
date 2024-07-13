import os
from app.database.models import async_session
from app.database.models import User, Teacher, Student, ScheduleForStudent, ScheduleForTeacher
from sqlalchemy import select, update, delete
import aiofiles

async def set_schedule_teachers():
    folder_path = 'schedule/teachers'
    files = os.listdir(folder_path)
    async with async_session() as session:
        for file in files:
            if file == 'parseT.py':
                continue
            file_path = os.path.join(folder_path, file)
            async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
                teacher = await f.readline()
                pos = teacher.find('-')
                teacher = teacher[0:pos-1].strip()
                print(teacher)
                existing_teacher = await session.scalar(select(ScheduleForTeacher).filter(ScheduleForTeacher.Teacher == teacher))
                schedule = None
                if not existing_teacher:
                    schedule = ScheduleForTeacher(Teacher=teacher)
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
                        if existing_teacher:
                            if current_day == 'Понедельник':
                                existing_teacher.Monday = block
                            elif current_day == 'Вторник':
                                existing_teacher.Tuesday = block
                            elif current_day == 'Среда':
                                existing_teacher.Wednesday = block
                            elif current_day == 'Четверг':
                                existing_teacher.Thursday = block
                            elif current_day == 'Пятница':
                                existing_teacher.Friday = block
                            elif current_day == 'Суббота':
                                existing_teacher.Saturday = block
                    else:
                        i += 1
        await session.commit()
        print('Commited')
