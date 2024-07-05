import asyncio
import sys
import os
from aiogram import Bot, Dispatcher
from app.handlers import router
from app.database.models import async_main
from dotenv import load_dotenv


async def main():
    await async_main()
    load_dotenv()
    bot = Bot(token=os.getenv('TOKEN'))
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Bot Shutting')
    except:
        print('Unexpected error:', sys.exc_info()[0])
