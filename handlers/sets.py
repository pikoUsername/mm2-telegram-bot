import json

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Set, SetItem
from db.repos import get_all_sets, add_set_command, add_set, search_sets, change_set

import logging

# URL для отправки данных в сторонний сервис
logger = logging.getLogger(__name__)

router = Router(name="Sets router")


@router.message(Command('set_list'))
async def set_lists(message: Message, session: AsyncSession):
	"""Список сетов в боте, пример: /set_list 0 10"""
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

	response = await get_all_sets(session, start, limit)
	if not response:
		return await message.answer("В боте нету сетов")
	text = "Все доступные сеты в боте:\n"
	for i, s in enumerate(response):
		_temp = f"{i + 1}: Сет с названием: '{s.set_name}' Предметы в сете:\n"
		for item in s.items:
			_temp += f"{item.item_name}: {item.amount}x\n"
		text += _temp
		text += "\n"

	await message.answer(text)


@router.message(Command('add_set'))
async def add_set_handler(message: Message, session: AsyncSession):
	"""Добавление сетов в бд через аргументы или JSON"""

	# Если в сообщении есть прикрепленный файл, пытаемся обработать его как JSON
	if message.document:
		# Скачиваем файл
		document = message.document
		file = await message.bot.download(document)

		try:
			# Чтение и парсинг содержимого файла
			json_data = json.load(file)

			# Обрабатываем каждый сет из JSON
			for set_name, items in json_data.items():

				# Формируем список объектов SetItem для каждого предмета
				set_items = [
					SetItem(item_name=item['name'], amount=item['amount'])
					for item in items
				]

				if set := await search_sets(session, set_name):
					set.items = set_items
					await change_set(session, set)
					logger.info("Found set in db, changed items")
					continue

				# Создаем объект Set и сохраняем в БД
				new_set = Set(set_name=set_name, items=set_items)
				await add_set(session, new_set, set_items)

			# Отправляем сообщение об успешном добавлении всех сетов
			await message.answer("Все сеты успешно добавлены из файла.")
		except json.JSONDecodeError:
			await message.answer("Ошибка: неверный формат JSON.")
		except Exception as e:
			await message.answer(f"Произошла ошибка при обработке файла: {str(e)}")
	else:
		response = await add_set_command(session, message.text)
		await message.answer(response)
