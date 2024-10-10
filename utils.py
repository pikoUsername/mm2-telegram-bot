import logging
import re
from datetime import timedelta, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database import Transaction, Item as ItemEntity, Set, SetItem
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


async def get_recent_transactions(session, start: int = 0, limit: int = 10):
	# Получение транзакций с заданным смещением (start) и лимитом (limit)
	query = (
		select(Transaction)
		.options(joinedload(Transaction.items))  # Загрузка связанных предметов
		.order_by(Transaction.timestamp.desc())  # Сортировка по времени
		.offset(start)  # Смещение от начала
		.limit(limit)  # Лимит на количество транзакций
	)

	result = await session.execute(query)
	transactions = result.scalars().unique().all()

	return transactions


async def find_set_by_name(session, set_name: str) -> Set | None:
	# Поиск сета по названию
	result = await session.execute(select(Set).where(Set.set_name == set_name))
	return result.scalars().first()


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


async def add_set_command(session: AsyncSession, message: str) -> str:
	# Регулярное выражение для парсинга команды
	set_pattern = r"/add_set ([\w\s]+) \(([\w\s]+) x(\d+)\)(?:; \(([\w\s]+) x(\d+)\))*"
	match = re.match(set_pattern, message)

	if not match:
		return "Неверный формат команды. Пример: /add_set Blue set (Red seer x1); (Fire fox x2)"

	set_name = match.group(1)
	item_1_name = match.group(2)
	item_1_amount = int(match.group(3))

	# Проверяем, есть ли второй предмет (он необязателен)
	item_2_name = match.group(4) if match.group(4) else None
	item_2_amount = int(match.group(5)) if match.group(5) else None

	# Проверка: существует ли сет с таким названием
	existing_set = await session.execute(select(Set).where(Set.set_name == set_name))
	existing_set = existing_set.scalars().first()

	if existing_set:
		return f"Сет с названием '{set_name}' уже существует."

	# Создаем новый сет
	new_set = Set(set_name=set_name)

	# Добавляем предметы в сет
	set_items = [SetItem(item_name=item_1_name, amount=item_1_amount, set=new_set)]

	if item_2_name:
		set_items.append(SetItem(item_name=item_2_name, amount=item_2_amount, set=new_set))

	# Добавляем сет и его предметы в базу
	session.add(new_set)
	session.add_all(set_items)
	await session.commit()

	return f"Сет '{set_name}' успешно добавлен с предметами: {item_1_name} x{item_1_amount}" + (
		f", {item_2_name} x{item_2_amount}" if item_2_name else "")
