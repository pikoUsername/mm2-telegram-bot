import logging
import re
from datetime import timedelta, datetime

from sqlalchemy import func, select

from database import Transaction, Item as ItemEntity
from schemas import ParsedMessageResult, Item


logger = logging.getLogger(__name__)


async def get_analytics(session):
	now = datetime.utcnow()

	# Аналитика за последнюю неделю
	week_ago = now - timedelta(days=7)
	month_ago = now - timedelta(days=30)

	# Запросы для аналитики
	week_transactions = await session.execute(
		select(func.count(Transaction.id)).filter(Transaction.timestamp >= week_ago)
	)
	month_transactions = await session.execute(
		select(func.count(Transaction.id)).filter(Transaction.timestamp >= month_ago)
	)
	total_transactions = await session.execute(
		select(func.count(Transaction.id))
	)

	# Подсчет потраченных средств
	week_spent = await session.execute(
		select(func.sum(Transaction.total_price)).where(Transaction.timestamp >= week_ago)
	)
	month_spent = await session.execute(
		select(func.sum(Transaction.total_price)).where(Transaction.timestamp >= month_ago)
	)
	total_spent = await session.execute(
		select(func.sum(Transaction.total_price))
	)

	return {
		'week_transactions': week_transactions.scalar(),
		'month_transactions': month_transactions.scalar(),
		'total_transactions': total_transactions.scalar(),
		'week_spent': week_spent.scalar() or 0,
		'month_spent': month_spent.scalar() or 0,
		'total_spent': total_spent.scalar() or 0
	}


async def get_items_report(session):
	# Группировка по типам предметов и подсчет общего количества
	items_report = await session.execute(
		select(
			ItemEntity.item_name,
			func.count(ItemEntity.item_name),
			func.sum(ItemEntity.amount)
		).group_by(ItemEntity.item_name)
	)

	return items_report.all()


def parse_message(text: str) -> ParsedMessageResult | None:
	# Регулярные выражения для извлечения данных
	item_pattern = r"(\d+)\. ([\w\s]+): (\d+) \((\d+) x (\d+)\)"
	roblox_pattern = r"Ваш_ник_в_ROBLOX: (\w+)"
	transaction_id_pattern = r"Transaction ID: (\d+)"
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
		transaction_id=transaction_id.group(1),
		total_price=total_price,
	)
