import logging
from typing import Sequence

import requests
from aiogram import Dispatcher
from aiogram.dispatcher.event.handler import HandlerObject
from aiogram.filters import Command
from aiogram.types import BotCommand

from settings import SERVICE_API_URL

logger = logging.getLogger(__name__)


def send_to_service(data):
	try:
		logger.info(f"data on the way: {data}")
		response = requests.post(SERVICE_API_URL, json=data)
		response.raise_for_status()
		return response.json()
	except requests.RequestException as e:
		logging.error(f"Failed to send data to service: {e}")
		return None


def extract_commands(dp: Dispatcher) -> list[BotCommand]:
	commands = []
	handlers: list[HandlerObject] = [*dp.message.handlers]

	for router in dp.sub_routers:
		handlers.extend(router.message.handlers)

	for handler in handlers:
		if not handler.callback.__doc__:
			logger.warning(f"Handler: {handler.callback.__name__} does not have any documentation")
		commands.extend(
			BotCommand(
				command=f.callback.commands[0],
				description=handler.callback.__doc__ or "Нету описания"
			) for f in handler.filters if isinstance(f.callback, Command)
		)

	return commands
