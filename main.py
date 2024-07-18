import asyncio
import sys
import os
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.handlers import router
from app.database.models import async_main
from dotenv import load_dotenv
from app import handlers
from app.database import requests
from datetime import datetime, timedelta
import pytz
from app.database.add_schedule__to_db_for_students import set_schedule_for_students
from app.database.add_schedule_for_teachers_to_db import set_schedule_teachers


# async def main():
#     await async_main()
#     load_dotenv()
#     bot = Bot(token=os.getenv('TOKEN'))
#     dp = Dispatcher()
#     dp.include_router(router)
#     # Первый раз запускаем с нижней строчкой, когда в терминале увидели commited, останавливаем и запускаем еще раз с этой строчкой, увидели commited - останавливаем, проверяем БД если все на месте убираем эту строку(комментируем).
#     await asyncio.gather(dp.start_polling(bot), set_schedule_teachers())
#     #для студентов
#     # await asyncio.gather(dp.start_polling(bot), set_schedule_for_students())
#
#
# if __name__ == '__main__':
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print('Bot Shutting')

async def main():
    await async_main()
    load_dotenv()
    bot = Bot(token=os.getenv('TOKEN'))
    dp = Dispatcher()
    dp.include_router(router)
    scheduler = AsyncIOScheduler(timezone='Europe/Moscow')
    scheduler.add_job(handlers.check_pair_and_send_message, trigger='cron', hour=16, minute=16, kwargs={'bot': bot})
    scheduler.add_job(handlers.check_pair_and_send_message, trigger='cron', hour=10, minute=55, kwargs={'bot': bot})
    scheduler.add_job(handlers.check_pair_and_send_message, trigger='cron', hour=12, minute=45, kwargs={'bot': bot})
    scheduler.add_job(handlers.check_pair_and_send_message, trigger='cron', hour=19, minute=36, kwargs={'bot': bot})
    scheduler.add_job(handlers.check_pair_and_send_message, trigger='cron', hour=16, minute=25, kwargs={'bot': bot})
    scheduler.add_job(handlers.check_pair_and_send_message, trigger='cron', hour=18, minute=15, kwargs={'bot': bot})
    scheduler.add_job(handlers.check_pair_and_send_message, trigger='cron', hour=19, minute=55, kwargs={'bot': bot})
    scheduler.add_job(handlers.check_pair_and_send_message, trigger='cron', hour=19, minute=55, kwargs={'bot': bot})
    scheduler.add_job(requests.forced_closure, trigger='cron', hour=14, minute=16)
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Bot Shutting')