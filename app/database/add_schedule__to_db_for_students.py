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
                    print('in')
                    schedule = ScheduleForStudent(group=group.strip())
                    session.add(schedule)

                current_day = None

                # async for line in f:
                #     current = line.strip()
                #     if len(current) == 0:
                #         continue
                #     elif current in ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']:
                #         if current_day and schedule:
                #             print(f"{current_day}: {getattr(schedule, current_day)}")
                #         current_day = current
                #         if schedule:
                #             setattr(schedule, current_day, '')
                #     elif current_day and schedule:
                #         current_pairs = getattr(schedule, current_day)
                #         setattr(schedule, current_day, current_pairs + current + '\n')
                #
                # if current_day and schedule:
                #     print(f"{current_day}: {getattr(schedule, current_day)}")

        await session.commit()
        print('Commited')






