import re
from typing import Sequence

from db.models import Alias
from schemas import ParsedMessageResult, Item
from utils import logger


def format_aliases(aliases: Sequence[Alias]) -> str:
	text = "Псевдонимы предметов:\n"

	for i, alias in enumerate(aliases):
		text += f"{i + 1}. Оригинальное имя - {alias.origin_name}, Псевдоним - {alias.alias_name}\n"

	return text


async def format_recent_transactions(transactions):
	# Формируем сообщение о последних транзакциях
	message = "Последние транзакции:\n"

	for transaction in transactions:
		message += f"\nТранзакция ID: {transaction.transaction_id}\n"
		message += f"ROBLOX имя: {transaction.roblox_name}\n"
		message += f"Общая сумма: {transaction.total_price} RUB\n"
		message += f"Дата: {transaction.timestamp}\n"
		message += "Предметы:\n"

		for item in transaction.items:
			message += f"  - {item.item_name}: {item.amount} шт. по {item.unit_price} RUB (Итого: {item.total_price} RUB)\n"

	return message


def parse_message(text: str) -> ParsedMessageResult | None:
	# Регулярные выражения для извлечения данных
	item_pattern = r"(\d+)\. ([\w\s]+): (\d+) \((\d+) x (\d+)\)"
	roblox_pattern = r"Ваш_ник_в_ROBLOX: (\w+)"
	transaction_id_pattern = r"Transaction ID: (\d+):(\d+)"
	total_price_pattern = r"Payment Amount: (\d+)"

	items = re.findall(item_pattern, text)
	roblox_name = re.search(roblox_pattern, text)
	transaction_id = re.search(transaction_id_pattern, text)
	total_price_match = re.search(total_price_pattern, text)

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

	# Преобразуем общую сумму платежа в число
	total_price = float(total_price_match.group(1))

	return ParsedMessageResult(
		items=parsed_items,
		roblox_username=roblox_name.group(1),
		transaction_id=transaction_id.group(2),
		total_price=total_price,
	)
