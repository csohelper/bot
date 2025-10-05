from aiogram import Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.keyboard import InlineKeyboardBuilder

from python.storage.command_loader import get_all_triggers
from python.storage.strings import get_string

router = Router()

_bot_username: str
_bot: Bot


async def init(bot_username: str, bot: Bot):
    global _bot_username, _bot
    _bot_username = bot_username
    _bot = bot


@router.message(lambda message: message.text and message.text.lower() in get_all_triggers('hype_collector_greeting'))
async def greet(message: Message):
    await message.delete()
    await message.reply(
        get_string(None, 'hype_collector.greeting'),
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(
                text=get_string(None, 'hype_collector.start'),
                url=await create_start_link(
                    _bot,
                    get_string(None, "payloads.hype_collector_start"),
                    encode=True
                )
            )
        ).as_markup()
    )


async def start_collector_command(message: Message, state: FSMContext):
    pass
