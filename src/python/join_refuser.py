import asyncio

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

from python.logger import logger
from python.storage.config import config
from python.storage.repository import users_repository
from python.storage.strings import get_string
from python.utils import await_and_run

_bot: Bot
_storage: BaseStorage


async def init(bot: Bot, storage: BaseStorage):
    global _bot, _dp
    _bot = bot
    _storage = storage


async def refuser_loop_check() -> None:
    logger.debug("Refuser loop check")
    requests = await users_repository.pop_unprocessed_requests_older_than(
        config.refuser.request_life_hours
    )
    if len(requests) > 0:
        logger.debug(f"Refuser: {requests} old requests")
    for request in requests:
        logger.debug(f"Refuser: {request.user_id} {request.created_at} refused")

        # Refusing request
        try:
            await _bot.decline_chat_join_request(config.chat_config.chat_id, request.user_id)
        except Exception as e:
            logger.error(f"Refuser: {str(e)}")

        #Sending message
        try:
            await _bot.send_message(
                request.user_id,
                get_string(
                    'user_service.moderation.auto_refused',
                    config.refuser.request_life_hours
                ),
                reply_markup=ReplyKeyboardRemove()
            )
        except TelegramForbiddenError as e:
            logger.debug(f"Refuser: {e.message}")

        # Clearing FSM state
        key = StorageKey(chat_id=request.user_id, user_id=request.user_id, bot_id=_bot.id)
        await _storage.set_state(key, state=None)
        await _storage.set_data(key, {})

    asyncio.create_task(await_and_run(config.refuser.refuser_check_time, refuser_loop_check))
