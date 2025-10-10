import asyncio
import datetime
import random

from aiogram import Bot, Router
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.types import ChatPermissions, Message

from .. import anecdote_poller
from ..logger import logger
from ..storage.config import config
from ..storage.strings import get_string
from ..utils import check_blacklisted, await_and_run

router = Router()
_bot: Bot

kek_last_use = {}


async def init(bot: Bot):
    global _bot
    _bot = bot


@router.message(Command("kek"))
@router.message(lambda message: message.text and message.text.lower() in ["kek", "кек"])
async def command_anecdote_handler(message: Message) -> None:
    try:
        if await check_blacklisted(message):
            return
        if message.chat.type not in ['group', 'supergroup']:
            await message.reply(get_string(
                message.from_user.language_code, 'echo_commands.kek.only_group'
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
        antiflood_time = config.anecdote.antiflood_time
        remain = antiflood_time - int(delta.total_seconds())
        if delta < datetime.timedelta(seconds=antiflood_time):
            reply = await message.reply(get_string(
                message.from_user.language_code,
                'echo_commands.kek.too_many',
                message.from_user.full_name,
                antiflood_time,
                remain
            ))
            await asyncio.sleep(5)
            try:
                await message.delete()
            except Exception as e:
                logger.error(f"Failed delete user message", e, message=message)
            try:
                await reply.delete()
            except Exception as e:
                logger.error(f"Failed delete reply message", e, reply=reply, message=message)
            return

        if random.random() < 0.05:
            me = await _bot.get_me()
            bot_member = await _bot.get_chat_member(chat_id=message.chat.id, user_id=me.id)

            if bot_member.status == ChatMemberStatus.ADMINISTRATOR and bot_member.can_restrict_members:
                ban_time = random.randint(1, 30)
                reply = await message.reply(get_string(
                    message.from_user.language_code,
                    'echo_commands.kek.ban',
                    message.from_user.full_name,
                    ban_time
                ))
                user_member = await _bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)
                if user_member.status != ChatMemberStatus.MEMBER:
                    await reply.edit_text(get_string(
                        message.from_user.language_code,
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
                            message.from_user.language_code,
                            'echo_commands.kek.ban_error',
                            message.from_user.full_name,
                            ban_time
                        ))
                        logger.error("Failed to restrict user. User not admin and bot has rights", e, message=message)
            else:
                await message.reply(get_string(
                    message.from_user.language_code,
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
                    anecdote = await anecdote_poller.get_anecdote()
                    if anecdote:
                        await message.reply(get_string(
                            message.from_user.language_code,
                            'echo_commands.kek.anecdote',
                            anecdote.text,
                            anecdote.anecdote_id
                        ))
                        return
                except Exception as e:
                    logger.error("Failed to generate anecdote. Retrying...", e, message=message)
        await message.reply(get_string(
            message.from_user.language_code,
            'echo_commands.kek.not_found'
        ))
    except Exception as e:
        await message.reply(
            get_string(
                message.from_user.language_code,
                "exceptions.uncause",
                logger.error(e, message),
                config.chat_config.owner
            )
        )
