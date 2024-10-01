import dataclasses
import logging
import os

import requests
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from database import is_transaction_processed, save_transaction, Transaction, Item, async_session
from utils import parse_message, get_analytics, get_items_report

# URL для отправки данных в сторонний сервис
SERVICE_API_URL = f"{os.getenv('WEB_API_URL')}/api/{os.getenv('WEB_API_TOKEN')}"
logger = logging.getLogger(__name__)

# Логирование
logging.basicConfig(level=logging.INFO)


# Функция для отправки данных в сторонний сервис
def send_to_service(data):
	try:
		logger.info(f"data on the way: {data}")
		response = requests.post(SERVICE_API_URL, json=data)
		response.raise_for_status()
		return response.json()
	except requests.RequestException as e:
		logging.error(f"Failed to send data to service: {e}")
		return None


# Обработчик сообщений
async def handle_message(message: Message, session: async_sessionmaker):
	# Парсим сообщение
	parsed_data = parse_message(message.text)
	logger.info("Handling message")

	logger.info(f"Parsed data: {parsed_data}")
	if not parsed_data:
		return
	transaction_id = parsed_data.transaction_id
	logger.info(f"Handling message for {transaction_id}")
	# Проверяем, был ли обработан данный transaction_id

	if await is_transaction_processed(session, transaction_id):
		logger.warning("Transaction is already processed")
		return
	logging.info(f"Processing new transaction ID: {transaction_id}")

	# Отправляем данные в сторонний сервис
	result = send_to_service(dataclasses.asdict(parsed_data))
	if not result:
		await message.reply("Невозможно связаться с сервисом бота")
		return
	logging.info(f"Successfully sent data to service: {result}")

	transaction = Transaction(
		transaction_id=transaction_id,
		roblox_name=parsed_data.roblox_username,
		total_price=parsed_data.total_price,
	)
	items = []

	for item in parsed_data.items:
		items.append(
			Item(
				transaction_id=transaction_id,
				amount=item.amount,
				item_name=item.name,
				unit_price=item.unit_price,
			)
		)

	transaction.items.extend(items)

	# Сохраняем транзакцию как обработанную
	await save_transaction(session, transaction)

	await message.reply(f"Транзакция обработана успешна! id: {transaction.id}, tx_id: {transaction_id}")


async def send_analytics(message: Message):
	async with async_session() as session:
		analytics = await get_analytics(session)

		await message.answer(
			f"Аналитика за последнюю неделю:\n"
			f"Транзакций: {analytics['week_transactions']}\n"
			f"Потрачено: {analytics['week_spent']} RUB\n\n"
			f"Аналитика за последний месяц:\n"
			f"Транзакций: {analytics['month_transactions']}\n"
			f"Потрачено: {analytics['month_spent']} RUB\n\n"
			f"Аналитика за всё время:\n"
			f"Транзакций: {analytics['total_transactions']}\n"
			f"Потрачено: {analytics['total_spent']} RUB"
		)


async def send_items_report(message: Message):
	async with async_session() as session:
		items_report = await get_items_report(session)

		# Формирование сообщения
		report_message = "Отчёт о предметах:\n"
		if len(items_report) == 0:
			report_message += "Не было транзакции, или ошибка в подсчете"
		for item_name, total_quantity, total_sum in items_report:
			report_message += f"{item_name}: {total_quantity} шт.\n"

		await message.answer(report_message)
