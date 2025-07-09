import asyncio
import datetime
import random
from aiogram import Bot, Router
from ..storage.strings import get_string
from aiogram.types import Message
from aiogram.filters import Command
from ..logger import logger
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.types import ChatPermissions, Message
from ..storage.config import config
from .. import anecdote


router = Router()
_bot: Bot

kek_last_use = {}


async def init(bot: Bot):
    global _bot
    _bot = bot


@router.message(Command("kek"))
@router.message(lambda message: message.text and message.text.lower() in ["kek", "кек"])
async def command_anecdote_handler(message: Message) -> None:
    if message.chat.type not in ['group', 'supergroup']:
        await message.reply(get_string(
            'echo_commands.kek.only_group'
        ))
        return

    global kek_last_use
    if message.chat.id in kek_last_use:
        last_use_chat = kek_last_use[message.chat.id]
    else:
        last_use_chat = datetime.datetime(2000, 1, 1, 0, 0)

    if not message.from_user:
        return

    delta: datetime.timedelta = datetime.datetime.now() - last_use_chat
    if delta < datetime.timedelta(seconds=30):
        reply = await message.reply(get_string(
            'echo_commands.kek.too_many', 
            message.from_user.full_name,
            30 - int(delta.total_seconds())
        ))
        await asyncio.sleep(5)
        try:
            await message.delete()
        except Exception as e:
            logger.error(f"Failed delete user message {message}: {e}")
        try:
            await reply.delete()
        except Exception as e:
            logger.error(f"Failed delete reply message {reply}: {e}")
        return

    if random.random() < 0.05:
        me = await _bot.get_me()
        bot_member = await _bot.get_chat_member(chat_id=message.chat.id, user_id=me.id)

        if bot_member.status == ChatMemberStatus.ADMINISTRATOR and bot_member.can_restrict_members:
            ban_time = random.randint(1, 30)
            reply = await message.reply(get_string(
                'echo_commands.kek.ban',
                message.from_user.full_name,
                ban_time
            ))
            user_member = await _bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)
            if user_member.status == ChatMemberStatus.ADMINISTRATOR:
                await reply.edit_text(get_string(
                    'echo_commands.kek.ban_admin',
                    message.from_user.full_name
                ))
            else:
                try:
                    await _bot.restrict_chat_member(
                        chat_id=message.chat.id,
                        user_id=message.from_user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=datetime.datetime.now() + datetime.timedelta(minutes=ban_time)
                    )
                except TelegramBadRequest as e:
                    await reply.edit_text(get_string(
                        'echo_commands.kek.ban_error',
                        message.from_user.full_name,
                        ban_time
                    ))
                    logger.error(f"Failed to restrict user {message.from_user.id} in chat {message.chat.id}. User not admin and bot has rights\n{e}")
        else:
            await message.reply(get_string(
                'echo_commands.kek.ban_no_rights',
                message.from_user.full_name
            ))
        return

    kek_last_use[message.chat.id] = datetime.datetime.now()

    if config.anecdote.enabled:
        for i in range(100):
            if i % 5 == 0:
                try:
                    await _bot.send_chat_action(
                        chat_id=message.chat.id,
                        action='typing',
                        message_thread_id=message.message_thread_id
                    )
                except TelegramRetryAfter:
                    logger.warning("Telegram action type status restricted by flood control")
            try:
                text = await anecdote.get_anecdote()
                if text:
                    await message.reply(get_string(
                        'echo_commands.kek.anecdote',
                        text
                    ))
                    return                
            except Exception as e:
                logger.error(f"Failed to generate anecdote with exc {e}. Retrying...")
    await message.reply(get_string(
        'echo_commands.kek.not_found'
    ))
