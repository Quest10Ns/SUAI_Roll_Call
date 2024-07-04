from app.database.models import async_session
from app.database.models import User
from sqlalchemy import select, update,delete

async def set_user(tg_id):
    async with  async_session() as session:
        user= await session.scalar(select(User.telegram_id == tg_id))


        if not user:
            session.add(User(telegram_id = tg_id))
            await session.commit()
