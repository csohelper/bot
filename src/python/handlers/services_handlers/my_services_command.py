from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

_bot_username: str
_bot: Bot


async def init(bot_username: str, bot: Bot):
    global _bot_username, _bot
    _bot_username = bot_username
    _bot = bot


router = Router()


async def on_my_services(message: Message, state: FSMContext, lang=None) -> None:
    if lang is None:
        lang = message.from_user.language_code
    # TODO
    pass
