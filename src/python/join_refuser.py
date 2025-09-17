import asyncio

from aiogram import Bot
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

from python.logger import logger
from python.storage.config import config
from python.storage.repository import users_repository
from python.storage.strings import get_string
from python.utils import await_and_run

_bot: Bot


async def init(bot: Bot):
    global _bot
    _bot = bot


async def refuser_loop_check() -> None:
    logger.debug("Refuser loop check")
    requests = await users_repository.pop_unprocessed_requests_older_than(
        config.refuser.request_life_hours
    )
    if len(requests) > 0:
        logger.debug(f"Refuser: {requests} old requests")
    for request in requests:
        logger.debug(f"Refuser: {request.user_id} {request.created_at} refused")
        await _bot.send_message(
            request.user_id,
            get_string(
                'user_service.moderation.auto_refused',
                config.refuser.request_life_hours
            ),
            reply_markup=ReplyKeyboardRemove()
        )
        await _bot.decline_chat_join_request(config.chat_config.chat_id, request.user_id)

    asyncio.create_task(await_and_run(config.refuser.refuser_check_time, refuser_loop_check))
