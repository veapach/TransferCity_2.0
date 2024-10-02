import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import TG_TOKEN
from app.user import router
from app.database.models import async_main

async def main():
    await async_main()
    bot = Bot(token=TG_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    print('Бот запущен')
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

# TODO: Реферальная система, премиум подписка, фотка для топ 10, друзья, ежедневные награды