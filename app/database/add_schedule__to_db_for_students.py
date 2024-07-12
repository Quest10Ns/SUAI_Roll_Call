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
            async with aiofiles.open(file_path, mode='r') as f:
                group = await f.readline()
                existing_group = await session.scalar(select(ScheduleForStudent).where(ScheduleForStudent.group == group.strip()))
                if not existing_group:
                    session.add(ScheduleForStudent(group=group.strip()))
        await session.commit()
        print('Commited')


