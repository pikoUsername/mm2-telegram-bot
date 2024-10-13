import dataclasses
import logging

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Transaction, ItemEntity
from db.repos import is_transaction_processed, search_sets, save_transaction
from schemas import Item
from settings import CHAT_ID
from utils import send_to_service
from formatters import parse_message
import logging

# URL для отправки данных в сторонний сервис
logger = logging.getLogger(__name__)


router = Router(name='Message main')


@router.message(F.chat.id == CHAT_ID, F.message.text.startswith("Order"))
async def handle_message(message: Message, session: AsyncSession):
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
	for item in parsed_data.items:

		if item.name.endswith("set"):
			sets = await search_sets(session, item.name)
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
