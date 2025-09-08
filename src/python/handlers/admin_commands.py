from asyncio import sleep

from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message, ReactionTypeEmoji

from ..storage.config import config, save_config
from ..storage.strings import get_string

router = Router()

_bot_username: str
_bot: Bot


async def init(bot_username: str, bot: Bot):
    global _bot_username, _bot
    _bot_username = bot_username
    _bot = bot


@router.message(Command("initchat"))
async def init_chat(message: Message) -> None:
    if not config.chat_config.owner:
        reply = await message.reply(get_string("admin_commands.admin_not_install"))
        await sleep(3)
        await reply.delete()
        await message.delete()
        return
    if config.chat_config.owner != message.from_user.id:
        reply = await message.reply(get_string("admin_commands.not_admin"))
        await sleep(3)
        await reply.delete()
        await message.delete()
        return
    await message.react([ReactionTypeEmoji(emoji="🤝")])
    config.chat_config.chat_id = message.chat.id
    save_config(config)
    await sleep(3)
    await message.delete()


@router.message(Command("initadmin"))
async def init_admin(message: Message) -> None:
    if not config.chat_config.owner:
        reply = await message.reply(get_string("admin_commands.admin_not_install"))
        await sleep(3)
        await reply.delete()
        await message.delete()
        return
    if config.chat_config.owner != message.from_user.id:
        reply = await message.reply(get_string("admin_commands.not_admin"))
        await sleep(3)
        await reply.delete()
        await message.delete()
        return
    await message.react([ReactionTypeEmoji(emoji="🤝")])
    config.chat_config.admin_chat_id = message.chat.id
    save_config(config)
    await sleep(3)
    await message.delete()
