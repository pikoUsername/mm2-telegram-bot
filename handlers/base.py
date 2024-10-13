from aiogram import Dispatcher

from . import aliases, analytics, message, sets


def register_handlers(dp: Dispatcher):
	dp.include_routers(
		aliases.router,
		analytics.router,
		message.router,
		sets.router,
	)
