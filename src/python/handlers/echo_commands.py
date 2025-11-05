import asyncio
import datetime
import random
from dataclasses import dataclass
from typing import List

from aiogram import Router, Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command, CommandStart, CommandObject, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InputMediaPhoto, FSInputFile, ChatMemberRestricted
from aiogram.utils.payload import decode_payload

import python.logger as logger_module
from python import utils
from python.handlers.hype_collector import start_collector_command
from python.handlers.services_handlers.add_service_commands import on_addservice
from python.handlers.services_handlers.join_service import on_accept_join_process
from python.storage import cache as cache_module
from python.storage import config as config_module
from python.storage.command_loader import get_echo_commands, EchoCommand, TimeInfo, ImageFileInfo
from python.storage.repository.users_repository import check_user, UserRecord
from python.storage.strings import get_string, get_strings
from python.storage.times import get_time_status
from python.utils import check_blacklisted, log_exception, await_and_run

router = Router()
_bot: Bot


async def init(bot: Bot):
    global _bot
    _bot = bot


_echo_commands_cache = None
_handlers_registered = False  # Флаг для отслеживания регистрации


def get_echo_commands_cached():
    """Получить эхо-команды с кешированием."""
    global _echo_commands_cache
    if _echo_commands_cache is None:
        _echo_commands_cache = get_echo_commands()
    return _echo_commands_cache


def build_kwargs(working_status: List[TimeInfo], lang: str) -> dict[str, str]:
    status_ = {wk.key: get_time_status(wk.time, lang) for wk in working_status}
    return status_


class TriggerFilter(BaseFilter):
    def __init__(self, triggers: list[str]):
        self.triggers = [t.lower() for t in triggers]

    async def __call__(self, message: Message) -> bool:
        return bool(message.text and message.text.lower() in self.triggers)


async def create_delete_task(*messages: Message) -> None:
    """Добавить сообщения в кэш для автоматического удаления."""
    for message in messages:
        if message.chat.type in ('group', 'supergroup'):
            await cache_module.cache.insert_message(message.chat.id, message.message_id)
    await cache_module.cache.save()


@dataclass(frozen=True)
class ImagePath:
    path: str


@dataclass(frozen=True)
class ImageId:
    id: str


async def get_file_list(*files: ImageFileInfo) -> list[ImagePath | ImageId]:
    result = []
    for info in files:
        if info.file is not None:
            if info.file in cache_module.cache.images_caches:
                result.append(ImageId(cache_module.cache.images_caches[info.file]))
            else:
                result.append(ImagePath(info.file))
        elif info.cycle is not None:
            index = (cache_module.cache.image_index.get(info.cycle.name, 0) + 1) % len(info.cycle.files)
            cache_module.cache.image_index[info.cycle.name] = index
            await cache_module.cache.save()

            result.extend(
                await get_file_list(info.cycle.files[index])
            )
        elif info.random is not None:
            result.extend(
                await get_file_list(random.choice(info.random.files))
            )

    return result


def make_image_handler(command_info: EchoCommand):
    @router.message(Command(command_info.name))
    @router.message(TriggerFilter(command_info.triggers))
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
            # global images_caches, image_index
            delete_messages = [message]

            tries = 0
            while True:
                tries += 1
                file_list: list[ImagePath | ImageId] = await get_file_list(*command_info.images.files)
                media = []

                for file in file_list:
                    if isinstance(file, ImagePath):
                        media.append(InputMediaPhoto(
                            media=FSInputFile(file.path),
                            show_caption_above_media=command_info.images.caption_above
                        ))
                    elif isinstance(file, ImageId):
                        media.append(InputMediaPhoto(
                            media=file.id,
                            show_caption_above_media=command_info.images.caption_above
                        ))

                media[0].caption = get_string(
                    message.from_user.language_code, command_info.message_path,
                    **build_kwargs(command_info.times, message.from_user.language_code)
                )

                try:
                    reply = await _bot.send_media_group(
                        chat_id=message.chat.id,
                        media=media,
                        reply_to_message_id=message.message_id
                    )

                    for message, file in zip(reply, file_list):
                        if isinstance(file, ImagePath):
                            cache_module.cache.images_caches[file.path] = message.photo[-1].file_id
                    await cache_module.cache.save()
                    delete_messages.extend(reply)
                except Exception as e:
                    logger_module.logger.error(f"{e}")
                    affected = 0
                    for file in file_list:
                        if isinstance(file, ImageId):
                            affected += 1
                            del cache_module.cache.images_caches[file.id]
                            await cache_module.cache.save()
                    if affected == 0:
                        logger_module.logger.warning(f"Tried {tries} times send images")
                        if tries >= 10:
                            raise IOError("Too many tries to send images") from e
                    await asyncio.sleep(0.2)
                    continue

                break
            asyncio.create_task(create_delete_task(*delete_messages))

        except Exception as e:
            await log_exception(e, message)

    return echo_command_handler


def make_text_handler(command_info: EchoCommand):
    @router.message(Command(command_info.name))
    @router.message(TriggerFilter(command_info.triggers))
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
                command_info.message_path,
                **build_kwargs(command_info.times, message.from_user.language_code)
            ))
            asyncio.create_task(create_delete_task(message, sent))
        except Exception as e:
            await log_exception(e, message)

    return echo_command_handler


def make_handler(command_info: EchoCommand):
    if command_info.images and len(command_info.images.files) > 0:
        make_image_handler(command_info)
    else:
        make_text_handler(command_info)


def register_echo_handlers():
    """
    Регистрация хэндлеров для всех эхо-команд.

    Должна быть вызвана после инициализации всех систем хранения.
    """
    global _handlers_registered

    if _handlers_registered:
        logger_module.logger.warning("Echo handlers already registered, skipping")
        return

    logger_module.logger.info("Registering echo command handlers...")

    for echo_command in get_echo_commands_cached():
        make_handler(echo_command)

    _handlers_registered = True
    logger_module.logger.info(f"Registered {len(get_echo_commands_cached())} echo command handlers")


@router.message(CommandStart(deep_link=True))
async def command_start_handler(message: Message, command: CommandObject, state: FSMContext) -> None:
    try:
        if await check_blacklisted(message):
            return
        args = command.args
        payload = decode_payload(args)

        match payload:
            case 'addservice':
                await on_addservice(message, state, message.from_user.language_code)
            case _ if payload == get_string(None, "payloads.hype_collector_start"):
                await start_collector_command(message, state)
            case _ if payload == get_string(None, "payloads.greeting_button"):
                await on_accept_join_process(message, state)
            case _:
                logger_module.logger.error(f"Can't handle start payload - Args: {args}, Payload: {payload}")
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
        asyncio.create_task(create_delete_task(
            message, sent
        ))

        if message.chat.type == "private":
            if config_module.config.chat_config.owner == 0 or config_module.config.chat_config.owner is None:
                await message.answer(get_string(message.from_user.language_code, 'echo_commands.first_start'))
                config_module.config.chat_config.owner = message.from_user.id
                config_module.config.chat_config.owner_username = message.from_user.username
                await config_module.config.save_config(config_module.config)
            if await in_chat(
                    message.bot, message.chat.id, message.from_user.id
            ) and config_module.config.chat_config.invite_link:
                await message.answer(get_string(
                    message.from_user.language_code, 'echo_commands.invite',
                    invite=config_module.config.chat_config.invite_link
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
        asyncio.create_task(create_delete_task(message, sent))
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
        asyncio.create_task(create_delete_task(message, sent))
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
        asyncio.create_task(create_delete_task(message, sent))
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
        asyncio.create_task(create_delete_task(message, sent))
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
        asyncio.create_task(create_delete_task(message, sent))
    except Exception as e:
        await log_exception(e, message)


async def delete_cycle():
    try:
        # 1. Получаем сообщения, которые нужно удалить
        messages = cache_module.cache.get_old_messages(
            config_module.config.chat_config.echo_auto_delete_secs
        )

        if not messages:
            logger_module.logger.trace("Delete cycle: No messages to delete (cache empty or all fresh)")
            return

        logger_module.logger.debug(f"Delete cycle: Found {len(messages)} message(s) to delete")

        to_remove_from_cache = []
        failed_messages = []

        # 2. Удаляем каждое сообщение в Telegram
        for msg in messages:
            try:
                await _bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id)
                logger_module.logger.debug(f"Deleted message: chat_id={msg.chat_id}, message_id={msg.message_id}")
                to_remove_from_cache.append(msg)

            except TelegramBadRequest:
                # Сообщение не найдено - уже удалено или никогда не существовало
                logger_module.logger.debug(f"Message not found: chat_id={msg.chat_id}, message_id={msg.message_id}")
                to_remove_from_cache.append(msg)

            except Exception as e:
                # Другие ошибки - временные проблемы с API
                logger_module.logger.warning(
                    f"Failed to delete message in Telegram: chat_id={msg.chat_id}, "
                    f"message_id={msg.message_id}, error: {type(e).__name__}: {e}"
                )
                failed_messages.append(msg)

        # 3. Удаляем из кэша все обработанные сообщения
        if to_remove_from_cache:
            await cache_module.cache.delete_messages(*to_remove_from_cache)
            logger_module.logger.info(
                f"Successfully removed {len(to_remove_from_cache)} message(s) from cache"
            )

        # 4. Принудительно удаляем из кэша старые проблемные сообщения (>1 час)
        if failed_messages:
            from datetime import datetime, timedelta

            old_threshold = datetime.now() - timedelta(hours=1)
            old_failed = [msg for msg in failed_messages if msg.create_time < old_threshold]

            if old_failed:
                await cache_module.cache.delete_messages(*old_failed)
                logger_module.logger.warning(
                    f"Force-removed {len(old_failed)} old failed message(s) from cache "
                    f"(failed to delete for >1 hour)"
                )

            # Логируем только свежие ошибки
            recent_failed = [msg for msg in failed_messages if msg not in old_failed]
            if recent_failed:
                failed_ids = [(m.chat_id, m.message_id) for m in recent_failed]
                logger_module.logger.warning(f"Failed to delete {len(recent_failed)} message(s): {failed_ids}")

    except Exception as e:
        logger_module.logger.error(f"Unexpected error in delete_cycle: {type(e).__name__}: {e}", exc_info=True)
    finally:
        # 5. Перезапуск цикла
        asyncio.create_task(await_and_run(60, delete_cycle))
