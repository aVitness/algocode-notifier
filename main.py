import asyncio
import logging

from aiogram import Bot, Dispatcher

from config import *
from utils.routers import load_routers
from utils.standings import STANDINGS
from worker import task

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(disable_fsm=True)


async def main():
    for table in STANDINGS:
        await table.load()
    asyncio.create_task(task(bot, COOLDOWN))
    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


if __name__ == '__main__':
    load_routers(dispatcher)
    asyncio.run(main())
