import base64
import io
import urllib.parse

from aiogram import Bot, Router
from aiogram import types
from aiogram.filters import Command
from aiogram.types import InaccessibleMessage, InlineKeyboardButton, InputMediaPhoto, Message, \
    FSInputFile, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from python.logger import logger
from python.storage import services_repository
from python.storage.config import config
from python.storage.services_repository import Service
from python.storage.strings import get_string

_bot_username: str
_bot: Bot


async def init(bot_username: str, bot: Bot):
    global _bot_username, _bot
    _bot_username = bot_username
    _bot = bot
    await services_repository.init_database_module()


router = Router()


async def send_to_moderation(service: Service) -> None:
    if service.image:
        image_bytes = base64.b64decode(service.image)
        image_stream = io.BytesIO(image_bytes)
        media = BufferedInputFile(image_stream.read(), filename=f"preview.jpg")
    else:
        media = FSInputFile('./src/res/images/empty_service.jpg')

    await _bot.send_photo(
        chat_id=config.chat_config.admin_chat_id,
        photo=media,
        caption=get_string(
            "services.add_command.moderation_preview",
            service.name, service.cost,
            service.cost_per, service.description,
            service.owner
        )
    )
