import re

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Alias
from db.repos import get_alias, add_alias, get_aliases, remove_alias
from formatters import format_aliases
import logging


quotes_regex = re.compile(r'^/add_alias\s+"([^"]+)"\s+"([^"]+)"$')
# URL для отправки данных в сторонний сервис
logger = logging.getLogger(__name__)

router = Router(name="Alias router")


@router.message(Command('add_alias'))
async def assign_alias(message: Message, session: AsyncSession):
	"""Сделать псевдоним, пример: /add_alias "Rev. seer" "Revolver of seer" """
	match = quotes_regex.match(message.text)
	if not match:
		return await message.reply('Не правильный формат команды, пример: /add_alias "Rev. seer" "Revolver of seer"')

	origin_name = match.group(1)
	alias_name = match.group(2)

	existing_alias = await get_alias(session, origin_name)

	if existing_alias:
		return await message.answer(f"Такой псевдоним уже существует.")

	# Если алиас не существует, создаем новый
	new_alias = Alias(origin_name=origin_name, alias_name=alias_name)
	await add_alias(session, new_alias)
	return await message.answer(f"Псевдоним '{alias_name}' был успешно добавлен для имени: '{origin_name}'.")


@router.message(Command('aliases'))
async def handle_get_aliases(message: Message, session: AsyncSession):
	"""Получит список всех псевдонимов"""
	response = await get_aliases(session)
	result = format_aliases(response)

	await message.answer(result)


@router.message(Command('remove_alias'))
async def remove_alias_handler(message: Message, session: AsyncSession):
	"""Удалить псевдоним, пример: /remove_alias Rdr """
	origin_name = message.text.split(" ")[1]

	result = await remove_alias(session, origin_name)
	if not result:
		return await message.answer("Этот алиас не найден, формат: /remove_alias {origin_name}")

	return await message.answer("Успешно удален псевдоним")
