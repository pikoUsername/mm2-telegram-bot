from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, BotCommand
from database import async_session, create_tables
from handlers import handle_message, send_analytics, send_items_report

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
API_TOKEN = os.getenv('BOT_API_TOKEN')
CHAT_ID = os.getenv("CHAT_ID")

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


# Функция для загрузки последних сообщений после перезапуска
async def check_last_messages():
	last_messages = await bot.get_updates(limit=30)
	logger.info(f"last messages: {last_messages}")
	for update in last_messages:
		if update.message and update.message.chat.id == CHAT_ID:  # Проверяем ID чата
			message = update.message
			await handle_message(message, async_session)


# Главная точка входа
async def main():
	# Создаем таблицы базы данных, если их нет
	await create_tables()

	logger.info(f"checking last messages")
	# Проверяем последние сообщения при старте
	await check_last_messages()

	logger.info(f"Setup for {CHAT_ID} chat")

	async def _temp_handle_message(msg: Message):
		return await handle_message(msg, async_session)

	# Регистрация хэндлера для текстовых сообщений
	dp.message.register(send_analytics, Command('analytics'))
	dp.message.register(send_items_report, Command('items_report'))
	dp.message.register(_temp_handle_message, F.text)

	# Запуск поллинга
	await bot.set_my_commands(
		[
			BotCommand(command="analytics", description="Получить аналитику"),
			BotCommand(command="items_report", description="Получить аналитику по предметам"),
		]
	)

	await dp.start_polling(bot)


if __name__ == '__main__':
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		logger.info("Turned off")
