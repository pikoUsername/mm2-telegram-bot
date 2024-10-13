from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from db.repos import get_recent_transactions, get_items_report, get_analytics
from formatters import format_recent_transactions
import logging

# URL для отправки данных в сторонний сервис
logger = logging.getLogger(__name__)


router = Router(name="Analytics router")


@router.message(Command("recents"))
async def recent_transactions_handler(message: Message, session: AsyncSession):
	"""Недавние транзакции, пример: /recents 0 10"""
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

	# Получаем последние транзакции с учетом смещения
	transactions = await get_recent_transactions(session, start=start, limit=limit)

	if transactions:
		# Формируем сообщение
		formatted_message = await format_recent_transactions(transactions)
		await message.answer(formatted_message)
	else:
		await message.answer("Нет данных о последних транзакциях.")


@router.message(Command("items_report"))
async def send_items_report(message: Message, session: AsyncSession):
	"""Получить аналитику по предметам"""
	items_report = await get_items_report(session)

	# Формирование сообщения
	report_message = "Отчёт о предметах:\n"
	if len(items_report) == 0:
		report_message += "Не было транзакции, или ошибка в подсчете"
	for item_name, total_quantity, total_sum in items_report:
		report_message += f"{item_name}: {total_quantity} шт.\n"

	await message.answer(report_message)


@router.message(Command('analytics'))
async def send_analytics(message: Message, session: AsyncSession):
	"""Получить аналитику за какой либо период"""
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
