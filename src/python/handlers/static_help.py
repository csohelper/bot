from pathlib import Path

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message

from python.logger import logger
from python.storage.cache import cache
from python.storage.strings import get_string

router = Router()
_bot: Bot


async def init(bot: Bot):
    global _bot
    _bot = bot


async def on_start() -> None:
    """
    Do an update of help messages on startup
    """
    for pin_message in cache.help_pin_messages:
        try:
            await _bot.edit_message_text(
                text=get_string(
                    pin_message.lang,
                    "echo_commands.help"
                ),
                chat_id=pin_message.chat_id,
                message_id=pin_message.message_id
            )
        except TelegramBadRequest:
            # Message not modified
            pass
        except Exception as e:
            logger.error("Can't change pin help message", e)


@router.message(Command("statichelp"))
async def static_help(message: Message):
    send = await message.answer(
        text=get_string(
            message.from_user.language_code,
            "echo_commands.help"
        )
    )
    await message.delete()
    cache.add_pin_message(message.chat.id, send.message_id, message.from_user.language_code)
