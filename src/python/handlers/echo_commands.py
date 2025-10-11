import asyncio
import datetime
import random
from typing import List

from aiogram import Router, Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart, CommandObject, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InputMediaPhoto, FSInputFile, ChatMemberRestricted
from aiogram.utils.payload import decode_payload

from .hype_collector import start_collector_command
from .services_handlers.add_service_commands import on_addservice
from .services_handlers.join_service import on_accept_join_process
from .. import utils
from ..logger import logger
from ..main import log_exception
from ..storage.command_loader import get_echo_commands, EchoCommand, TimeInfo
from ..storage.config import config, save_config
from ..storage.repository.users_repository import check_user, UserRecord
from ..storage.strings import get_string, get_strings
from ..storage.times import get_time_status
from ..utils import check_blacklisted

router = Router()

echo_commands = get_echo_commands()


def build_kwargs(working_status: List[TimeInfo], lang: str) -> dict[str, str]:
    status_ = {wk.key: get_time_status(wk.time, lang) for wk in working_status}
    return status_


class TriggerFilter(BaseFilter):
    def __init__(self, triggers: list[str]):
        self.triggers = [t.lower() for t in triggers]

    async def __call__(self, message: Message) -> bool:
        return bool(message.text and message.text.lower() in self.triggers)


images_caches: dict[str, list[str]] = {}


async def check_and_delete_after(*messages: Message):
    await asyncio.sleep(config.chat_config.echo_auto_delete_secs)
    if messages[0].chat.id == config.chat_config.chat_id:
        for message in messages:
            await message.delete()


def make_image_handler(echo_command: EchoCommand):
    @router.message(Command(echo_command.name))
    @router.message(TriggerFilter(echo_command.triggers))
    async def echo_command_handler(message: Message) -> None:
        try:
            if await check_blacklisted(message):
                return
            if message.chat.type == "private":
                await check_user(UserRecord(
                    message.from_user.id,
                    message.from_user.username,
                    message.from_user.full_name,
                    message.from_user.language_code,
                ))
            global images_caches
            delete_messages = [message]
            while True:
                if (
                        echo_command.name not in images_caches or
                        images_caches[echo_command.name] is None or
                        len(images_caches[echo_command.name]) == 0
                ):
                    media = [
                        InputMediaPhoto(
                            media=FSInputFile(x),
                            show_caption_above_media=echo_command.images.caption_above
                        ) for x in echo_command.images.files
                    ]
                    media[0].caption = get_string(
                        message.from_user.language_code,
                        echo_command.message_path,
                        **build_kwargs(echo_command.times, message.from_user.language_code)
                    )
                    sent = await message.reply_media_group(media=media)

                    images_caches[echo_command.name] = []
                    for msg in sent:
                        delete_messages.append(msg)
                        if msg.photo:
                            largest_photo = msg.photo[-1]
                            images_caches[echo_command.name].append(largest_photo.file_id)
                else:
                    try:
                        media = [
                            InputMediaPhoto(
                                media=file_id,
                                show_caption_above_media=echo_command.images.caption_above
                            ) for file_id in images_caches[echo_command.name]
                        ]
                        media[0].caption = get_string(
                            message.from_user.language_code, echo_command.message_path,
                            **build_kwargs(echo_command.times, message.from_user.language_code)
                        )
                        delete_messages.extend(await message.reply_media_group(media=media))
                    except Exception as e:
                        logger.error(f"{e}")
                        images_caches[echo_command.name] = []
                        continue
                break
            asyncio.create_task(check_and_delete_after(*delete_messages))
        except Exception as e:
            await log_exception(e, message)

    return echo_command_handler


def make_text_handler(echo_command: EchoCommand):
    @router.message(Command(echo_command.name))
    @router.message(TriggerFilter(echo_command.triggers))
    async def echo_command_handler(message: Message) -> None:
        try:
            if await check_blacklisted(message):
                return
            if message.chat.type == "private":
                await check_user(UserRecord(
                    message.from_user.id,
                    message.from_user.username,
                    message.from_user.full_name,
                    message.from_user.language_code,
                ))
            sent = await message.reply(get_string(
                message.from_user.language_code,
                echo_command.message_path,
                **build_kwargs(echo_command.times, message.from_user.language_code)
            ))
            asyncio.create_task(check_and_delete_after(message, sent))
        except Exception as e:
            await log_exception(e, message)

    return echo_command_handler


def make_handler(echo_command: EchoCommand):
    if echo_command.images and len(echo_command.images.files) > 0:
        make_image_handler(echo_command)
    else:
        make_text_handler(echo_command)


for echo_command in echo_commands:
    make_handler(echo_command)


@router.message(CommandStart(deep_link=True))
async def command_start_handler(message: Message, command: CommandObject, state: FSMContext) -> None:
    try:
        if await check_blacklisted(message):
            return
        args = command.args
        payload = decode_payload(args)
        logger.debug(payload)

        match payload:
            case 'addservice':
                await on_addservice(message, state, message.from_user.language_code)
            case _ if payload == get_string(None, "payloads.hype_collector_start"):
                await start_collector_command(message, state)
            case _ if payload == get_string(None, "payloads.greeting_button"):
                await on_accept_join_process(message, state)
            case _:
                logger.error(f"Can't handle start payload - Args: {args}, Payload: {payload}")
    except Exception as e:
        await log_exception(e, message)


async def in_chat(bot: Bot, chat_id: int, user_id: int) -> bool:
    """
    Проверяет, состоит ли пользователь в чате.
    Возвращает True, если пользователь сейчас в чате (любым статусом, кроме left/kicked).
    Возвращает False, если его нет, он забанен, вышел или никогда не был.
    """
    try:
        m = await bot.get_chat_member(chat_id, user_id)
    except TelegramAPIError:
        # сюда попадём, если пользователь никогда не был в чате
        # или бот не имеет доступа к информации
        return False

    if m.status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
        return False
    if isinstance(m, ChatMemberRestricted):
        return m.is_member
    return True


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    try:
        if await check_blacklisted(message):
            return
        sent = await message.reply(get_string(message.from_user.language_code, 'echo_commands.start'))
        asyncio.create_task(check_and_delete_after(
            message, sent
        ))

        if message.chat.type == "private":
            if config.chat_config.owner == 0:
                await message.answer(get_string(message.from_user.language_code, 'echo_commands.first_start'))
                config.chat_config.owner = message.from_user.id
                save_config(config)
            if await in_chat(message.bot, message.chat.id, message.from_user.id) and config.chat_config.invite_link:
                await message.answer(get_string(
                    message.from_user.language_code, 'echo_commands.invite',
                    invite=config.chat_config.invite_link
                ))

    except Exception as e:
        await log_exception(e, message)


@router.message(Command("mei"))
@router.message(lambda message: message.text and message.text.lower() in ["мэи", "меи"])
async def command_mei_handler(message: Message) -> None:
    try:
        if await check_blacklisted(message):
            return
        sent = await message.reply(
            random.choice(
                get_strings(message.from_user.language_code, 'echo_commands.mei')
            )
        )
        asyncio.create_task(check_and_delete_after(message, sent))
    except Exception as e:
        await log_exception(e, message)


@router.message(Command("meishniky"))
@router.message(lambda message: message.text and message.text.lower() in ["мэишники", "меишники"])
async def command_meishniky_handler(message: Message) -> None:
    try:
        if await check_blacklisted(message):
            return
        sent = await message.reply(
            random.choice(
                get_strings(message.from_user.language_code, 'echo_commands.meishniky')
            )
        )
        asyncio.create_task(check_and_delete_after(message, sent))
    except Exception as e:
        await log_exception(e, message)


@router.message(Command("mai"))
@router.message(lambda message: message.text and message.text.lower() in ["маи"])
async def command_mai_handler(message: Message) -> None:
    try:
        if await check_blacklisted(message):
            return
        sent = await message.reply(
            random.choice(
                get_strings(message.from_user.language_code, 'echo_commands.mai')
            )
        )
        asyncio.create_task(check_and_delete_after(message, sent))
    except Exception as e:
        await log_exception(e, message)


@router.message(Command("maishniki"))
@router.message(lambda message: message.text and message.text.lower() in ["маишники", "маёвцы"])
async def command_maishniky_handler(message: Message) -> None:
    try:
        if await check_blacklisted(message):
            return
        sent = await message.reply(
            random.choice(
                get_strings(message.from_user.language_code, 'echo_commands.maishniky')
            )
        )
        asyncio.create_task(check_and_delete_after(message, sent))
    except Exception as e:
        await log_exception(e, message)


@router.message(Command("week"))
@router.message(lambda message: message.text and message.text.lower() in ["неделя"])
async def command_week_handler(message: Message) -> None:
    try:
        if await check_blacklisted(message):
            return
        week_number = utils.get_week_number(datetime.datetime.now())
        sent = await message.reply(
            get_string(
                message.from_user.language_code,
                'echo_commands.week',
                get_strings(message.from_user.language_code, 'echo_commands.week_types_up_down')[week_number % 2],
                get_strings(message.from_user.language_code, 'echo_commands.week_types_even')[week_number % 2],
                week_number
            )
        )
        asyncio.create_task(check_and_delete_after(message, sent))
    except Exception as e:
        await log_exception(e, message)
