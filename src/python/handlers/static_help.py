import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message

from python.logger import logger
from python.storage import cache as cache_module, config
from python.storage.strings import get_string
from python.utils import log_exception

router = Router()
_bot: Bot


async def init(bot: Bot):
    global _bot
    _bot = bot


async def on_start() -> None:
    """
    Do an update of help messages on startup
    """
    tz = None
    if config.config.timezone:
        tz = ZoneInfo(config.config.timezone)
    strftime = datetime.datetime.now(tz).strftime("%d.%m.%Y")
    for pin_message in cache_module.cache.help_pin_messages:
        try:
            await _bot.edit_message_text(
                text=get_string(
                    pin_message.lang,
                    "echo_commands.static_help",
                    date=strftime,
                    help=get_string(
                        pin_message.lang,
                        "echo_commands.help"
                    )
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
    """
    Sends help message and storing message id in cache_module.caches for future auto-updates
    """
    try:
        send = await message.answer(
            text=get_string(
                message.from_user.language_code,
                "echo_commands.help"
            )
        )
        await message.delete()
        await cache_module.cache.add_pin_message(message.chat.id, send.message_id, message.from_user.language_code)
    except Exception as e:
        await log_exception(e, message)
