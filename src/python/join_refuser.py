import asyncio

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from aiogram.types import ReplyKeyboardRemove

from python.logger import logger
from python.storage.config import config
from python.storage.repository import users_repository
from python.storage.strings import get_string
from python.utils import await_and_run

_bot: Bot
_storage: BaseStorage


async def init(bot: Bot, storage: BaseStorage):
    global _bot, _storage
    _bot = bot
    _storage = storage


async def refuser_loop_check() -> None:
    logger.trace("Refuser loop check")
    requests = await users_repository.pop_unprocessed_requests_older_than(
        config.refuser.request_life_hours
    )
    if len(requests) > 0:
        logger.debug(f"Refuser: {len(requests)} old requests")
    for request in requests:
        logger.debug(f"Refuser: #{request.user_id} - ({request.created_at}) refused")

        # Refusing request
        try:
            await _bot.decline_chat_join_request(config.chat_config.chat_id, request.user_id)
        except Exception as e:
            logger.error(f"Refuser: Can't decline request")
            logger.error(e)

        # Sending message
        try:
            await _bot.send_message(
                request.user_id,
                get_string(
                    request.lang,
                    'user_service.auto_refused',
                    config.refuser.request_life_hours
                ),
                reply_markup=ReplyKeyboardRemove()
            )
        except TelegramForbiddenError as e:
            if request.greeting_msg:
                try:
                    logger.debug(f"Refuser: {request.user_id} banned bot, trying edit old message")
                    await _bot.edit_message_text(
                        text=get_string(
                            request.lang,
                            'greeting_start_refused.greeting_start_refused',
                            config.refuser.request_life_hours
                        ),
                        chat_id=request.user_id,
                        message_id=request.greeting_msg
                    )
                except Exception as e2:
                    try:
                        logger.debug(f"Refuser: Can't edit message, trying delete old message")
                        await _bot.delete_message(
                            chat_id=request.user_id,
                            message_id=request.greeting_msg
                        )
                    except Exception as e3:
                        logger.error(f"Refuser:")
                        logger.error(e)
                        logger.error(e2)
                        logger.error(e3)
            else:
                logger.error(f"Refuser: Can't send new message, old not found")
                logger.error(e)

        try:
            # Clearing FSM state
            key = StorageKey(chat_id=request.user_id, user_id=request.user_id, bot_id=_bot.id)
            await _storage.set_state(key, state=None)
            await _storage.set_data(key, {})
        except Exception as e:
            logger.error(f"Refuser: Can't clear FSM state")
            logger.error(e)

    asyncio.create_task(await_and_run(config.refuser.refuser_check_time, refuser_loop_check))
