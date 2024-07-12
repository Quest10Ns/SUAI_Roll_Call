import asyncio
import sys
import os
from aiogram import Bot, Dispatcher
from app.handlers import router
from app.database.models import async_main
from dotenv import load_dotenv
from app.database.add_schedule__to_db_for_students import set_schedule_for_students

async def main():
    await async_main()
    load_dotenv()
    bot = Bot(token=os.getenv('TOKEN'))
    dp = Dispatcher()
    dp.include_router(router)

    # Запуск бота и функции set_schedule_for_students одновременно
    await asyncio.gather(dp.start_polling(bot), set_schedule_for_students())

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Bot Shutting')
