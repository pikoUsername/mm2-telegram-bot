import dataclasses
import logging
import os

import requests
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from database import is_transaction_processed, save_transaction, Transaction, ItemEntity, async_session
from schemas import Item
from utils import parse_message, get_analytics, get_items_report, get_recent_transactions, format_recent_transactions, \
	add_set_command, search_sets, get_all_sets

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
	if not parsed_data:
		logger.warning("Not found items in parsed message")
		return
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

	actual_items = []
	async with async_session() as sess:
		for item in parsed_data.items:

			if item.name.endswith("set"):
				sets = await search_sets(sess, item.name)
				if not sets:
					continue
				items = [
					Item(
						name=i.name,
						amount=i.amount,
						unit_price=0,
					) for i in sets.items
				]
				actual_items.extend(items)
			else:
				actual_items.append(item)
	parsed_data.items = actual_items

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
			ItemEntity(
				transaction_id=transaction_id,
				amount=item.amount,
				item_name=item.name,
				unit_price=item.unit_price,
			)
		)

	transaction.items.extend(items)

	# Сохраняем транзакцию как обработанную
	await save_transaction(session, transaction)

	await message.reply(f"Транзакция была отправлена в очередь. id: {transaction.id}, tx_id: {transaction_id}")


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


async def set_lists(message: Message, session: async_sessionmaker):
	# Получаем аргументы команды (если они есть)
	args = message.text.split(" ")
	args.remove(args[0])

	try:
		# Параметры по умолчанию
		start = 0
		limit = 10

		if len(args) == 1:
			# Если указан только лимит
			limit = int(args[0])
		elif len(args) == 2:
			# Если указаны начальная позиция и лимит
			start = int(args[0])
			limit = int(args[1])

		# Если указаны некорректные значения
		if limit <= 0 or start < 0:
			await message.answer("Ошибка: значения должны быть положительными числами.")
			return

	except ValueError:
		# Если произошла ошибка при преобразовании аргументов
		await message.answer("Ошибка: некорректный формат аргументов. Используйте /recents [start] [limit].")
		return

	async with session() as sus:
		response = await get_all_sets(sus, start, limit)

		text = "Все доступные сеты в боте:\n"
		for i, s in enumerate(response):
			_temp = f"{i + 1}: Сет с названием: '{s.set_name}' Предметы в сете:\n"
			for item in s.items:
				_temp += f"{item.item_name}: {item.amount}x\n"
			text += _temp
			text += "\n"

		await message.answer(text)


async def assign_alias(message: Message, session: async_sessionmaker):
	async with session() as sus:
		pass


async def handle_get_aliases(message: Message, session: async_sessionmaker):
	user_id = message.from_user.id
	response = await get_aliases(user_id, session)
	await message.answer(response)


async def add_set_handler(message: Message, session: async_sessionmaker):
	async with session() as sus:
		response = await add_set_command(sus, message.text)
		await message.answer(response)


async def recent_transactions_handler(message: Message):
	# Получаем аргументы команды (если они есть)
	args = message.text.split(" ")
	args.remove(args[0])

	try:
		# Параметры по умолчанию
		start = 0
		limit = 10

		if len(args) == 1:
			# Если указан только лимит
			limit = int(args[0])
		elif len(args) == 2:
			# Если указаны начальная позиция и лимит
			start = int(args[0])
			limit = int(args[1])

		# Если указаны некорректные значения
		if limit <= 0 or start < 0:
			await message.answer("Ошибка: значения должны быть положительными числами.")
			return

	except ValueError:
		# Если произошла ошибка при преобразовании аргументов
		await message.answer("Ошибка: некорректный формат аргументов. Используйте /recents [start] [limit].")
		return

	async with async_session() as session:
		# Получаем последние транзакции с учетом смещения
		transactions = await get_recent_transactions(session, start=start, limit=limit)

		if transactions:
			# Формируем сообщение
			formatted_message = await format_recent_transactions(transactions)
			await message.answer(formatted_message)
		else:
			await message.answer("Нет данных о последних транзакциях.")


async def send_items_report(message: Message, session: async_sessionmaker):
	async with session() as sus:
		items_report = await get_items_report(sus)

		# Формирование сообщения
		report_message = "Отчёт о предметах:\n"
		if len(items_report) == 0:
			report_message += "Не было транзакции, или ошибка в подсчете"
		for item_name, total_quantity, total_sum in items_report:
			report_message += f"{item_name}: {total_quantity} шт.\n"

		await message.answer(report_message)
