
import asyncio
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from aiogram import Bot, Dispatcher

from db.base import create_tables
from handlers.base import register_handlers
from middlewares.db import DbSessionMiddleware
from settings import DATABASE_URL, API_TOKEN, CHAT_ID
from utils import extract_commands

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
	engine = create_async_engine(url=DATABASE_URL, echo=False)
	sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

	await create_tables(engine)

	# Инициализация бота и диспетчера
	bot = Bot(token=API_TOKEN)
	dp = Dispatcher()
	dp.update.middleware(DbSessionMiddleware(session_pool=sessionmaker))

	logger.info(f"Setup for {CHAT_ID} chat")

	register_handlers(dp)

	commands = extract_commands(dp)
	logger.info(commands)
	# Запуск поллинга
	await bot.set_my_commands(commands)

	await dp.start_polling(bot)


if __name__ == '__main__':
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		logger.info("Turned off")
