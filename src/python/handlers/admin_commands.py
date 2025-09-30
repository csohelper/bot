from asyncio import sleep

from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message, ReactionTypeEmoji

from ..storage.config import config, save_config, BlacklistedChat
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
        reply = await message.reply(get_string(message.from_user.language_code, "admin_commands.admin_not_install"))
        await sleep(3)
        await reply.delete()
        await message.delete()
        return
    if config.chat_config.owner != message.from_user.id:
        reply = await message.reply(get_string(message.from_user.language_code, "admin_commands.not_admin"))
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
        reply = await message.reply(get_string(message.from_user.language_code, "admin_commands.admin_not_install"))
        await sleep(3)
        await reply.delete()
        await message.delete()
        return
    if config.chat_config.owner != message.from_user.id:
        reply = await message.reply(get_string(message.from_user.language_code, "admin_commands.not_admin"))
        await sleep(3)
        await reply.delete()
        await message.delete()
        return
    await message.react([ReactionTypeEmoji(emoji="🤝")])
    config.chat_config.admin_chat_id = message.chat.id
    save_config(config)
    await sleep(3)
    await message.delete()


def find_chat(blacklisted: list[BlacklistedChat], chat_id: int) -> BlacklistedChat | None:
    for chat in blacklisted:
        if chat.chat_id == chat_id:
            return chat
    return None


@router.message(Command("blacklist"))
async def blacklist(message: Message) -> None:
    if not config.chat_config.owner:
        reply = await message.reply(get_string(message.from_user.language_code, "admin_commands.admin_not_install"))
        await sleep(3)
        await reply.delete()
        await message.delete()
        return
    if config.chat_config.owner != message.from_user.id:
        reply = await message.reply(get_string(message.from_user.language_code, "admin_commands.not_admin"))
        await sleep(3)
        await reply.delete()
        await message.delete()
        return

    if message.chat.type == "supergroup" and message.chat.is_forum:
        await message.react([ReactionTypeEmoji(emoji="🤝")])
        chat = find_chat(config.blacklisted, message.chat.id)
        if not chat:
            chat = BlacklistedChat(chat_id=message.chat.id)
            config.blacklisted.append(chat)
        if not chat.topics:
            chat.topics = []
        chat.topics.append(message.message_thread_id)
    elif message.chat.type in ("supergroup", "group"):
        await message.react([ReactionTypeEmoji(emoji="🤝")])
        chat = find_chat(config.blacklisted, message.chat.id)
        if not chat:
            chat = BlacklistedChat(chat_id=message.chat.id)
            config.blacklisted.append(chat)
    else:
        await message.react([ReactionTypeEmoji(emoji="👎")])

    save_config(config)
    await sleep(3)
    await message.delete()


@router.message(Command("unblacklist"))
async def blacklist(message: Message) -> None:
    if not config.chat_config.owner:
        reply = await message.reply(get_string(message.from_user.language_code, "admin_commands.admin_not_install"))
        await sleep(3)
        await reply.delete()
        await message.delete()
        return
    if config.chat_config.owner != message.from_user.id:
        reply = await message.reply(get_string(message.from_user.language_code, "admin_commands.not_admin"))
        await sleep(3)
        await reply.delete()
        await message.delete()
        return

    if message.chat.type == "supergroup" and message.chat.is_forum:
        await message.react([ReactionTypeEmoji(emoji="🤝")])
        chat = find_chat(config.blacklisted, message.chat.id)
        if chat:
            chat.topics.remove(message.message_thread_id)
    elif message.chat.type in ("supergroup", "group"):
        chat = find_chat(config.blacklisted, message.chat.id)
        config.blacklisted.remove(chat)
    else:
        await message.react([ReactionTypeEmoji(emoji="👎")])

    save_config(config)
    await sleep(3)
    await message.delete()
