import dataclasses
import decimal
import re
import logging
import requests
import os
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import is_transaction_processed, save_transaction

# URL для отправки данных в сторонний сервис
SERVICE_API_URL = f"{os.getenv('WEB_API_URL')}/api/{os.getenv('WEB_API_TOKEN')}"
logger = logging.getLogger(__name__)

# Логирование
logging.basicConfig(level=logging.INFO)


@dataclasses.dataclass
class Item:
	name: str
	amount: int
	unit_price: float


@dataclasses.dataclass
class ParsedMessageResult:
	items: list[Item]
	roblox_username: str
	transaction_id: str


# Функция для парсинга сообщения
def parse_message(text: str) -> ParsedMessageResult | None:
	# Регулярные выражения для извлечения данных
	item_pattern = r"(\d+)\. ([\w\s]+): (\d+) \((\d+) x (\d+)\)"
	roblox_pattern = r"Ваш_ник_в_ROBLOX: (\w+)"
	transaction_id_pattern = r"Transaction ID: (\d+)"

	items = re.findall(item_pattern, text)
	roblox_name = re.search(roblox_pattern, text)
	transaction_id = re.search(transaction_id_pattern, text)
	logger.info(f'Transaction id: {transaction_id}, roblox_username: {roblox_name}')

	if not roblox_name or not transaction_id:
		return None  # Если не нашли обязательные данные

	parsed_items = []
	for item in items:
		parsed_items.append(Item(
			name=item[1],  # Название товара
			amount=int(item[3]),  # Количество заказанных товаров
			unit_price=float(item[4])
		))

	return ParsedMessageResult(
		items=parsed_items,
		roblox_username=roblox_name.group(1),
		transaction_id=transaction_id.group(1)
	)


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
async def handle_message(message: Message, session: AsyncSession):
	# Парсим сообщение
	parsed_data = parse_message(message.text)
	logger.info("Handling message")

	logger.info(f"Parsed data: {parsed_data}")
	if parsed_data:
		transaction_id = parsed_data.transaction_id
		logger.info(f"Handling message for {transaction_id}")
		# Проверяем, был ли обработан данный transaction_id

		if not await is_transaction_processed(session, transaction_id):
			logging.info(f"Processing new transaction ID: {transaction_id}")

			# Отправляем данные в сторонний сервис
			result = send_to_service(dataclasses.asdict(parsed_data))
			if result:
				logging.info(f"Successfully sent data to service: {result}")

				# Сохраняем транзакцию как обработанную
				await save_transaction(session, transaction_id)
