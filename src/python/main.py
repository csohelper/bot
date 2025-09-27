import asyncio
import platform

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, Message, ReplyKeyboardRemove
from aiogram.types.link_preview_options import LinkPreviewOptions
from redis.asyncio import from_url

from python import anecdote_poller, join_refuser
from python.handlers import echo_commands, images_echo_commands, kek_command, admin_commands
from python.handlers.services_handlers import add_service_commands, list_services_command, moderate_service, \
    join_service
from python.logger import logger
from python.storage import strings
from python.storage.config import config
from python.storage.database import open_database_pool, close_database_pool
from python.storage.repository import services_repository, users_repository, anecdotes_repository
from python.storage.strings import __get_locale_object, get_string, get_object
from python.storage.times import get_time
from python.utils import await_and_run

bot: Bot
dp: Dispatcher

default_router = Router()


@default_router.message(F.chat.type == "private")
async def default_private_handler(message: Message):
    await message.answer(
        get_string(message.from_user.language_code, "echo_commands.unknown"),
        reply_markup=ReplyKeyboardRemove()
    )


async def set_commands(commands_dict, lang: str | None):
    await bot.set_my_commands(
        [
            BotCommand(command=x['command'], description=x['description']) for x in commands_dict
        ],
        language_code=lang,
    )


async def main() -> None:
    global bot, dp
    bot = Bot(
        token=config.telegram.token,
        default=DefaultBotProperties(
            parse_mode=config.telegram.parse_mode,
            link_preview=LinkPreviewOptions(is_disabled=True),
            disable_notification=True
        )
    )
    if config.redis_config.enabled:
        redis = from_url(config.redis_config.url, decode_responses=config.redis_config.decode_responses)
        storage = RedisStorage(redis=redis)
    else:
        storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_routers(
        echo_commands.router,
        images_echo_commands.router,
        kek_command.router,
        add_service_commands.router,
        list_services_command.router,
        moderate_service.router,
        admin_commands.router,
        join_service.router,
        default_router  # Must be in ending
    )

    @dp.startup()
    async def on_startup():
        logger.info("Aiogram: starting bot")
        await open_database_pool()
        logger.info("Aiogram: bot started")
        await kek_command.init(bot=bot)
        bot_username = str((await bot.get_me()).username)
        await add_service_commands.init(bot_username=bot_username, bot=bot)
        await list_services_command.init(bot_username=bot_username, bot=bot)
        await moderate_service.init(bot_username=bot_username, bot=bot)
        await admin_commands.init(bot_username=bot_username, bot=bot)
        await join_refuser.init(bot=bot, storage=dp.storage)
        await join_service.init(bot=bot)
        await services_repository.init_database_module()
        await anecdotes_repository.init_database_module()
        await users_repository.init_database_module()
        if config.anecdote.enabled:
            asyncio.create_task(await_and_run(10, anecdote_poller.anecdote_loop_check))
        if config.refuser.enabled:
            asyncio.create_task(await_and_run(10, join_refuser.refuser_loop_check))

        await set_commands(get_object(None, "commands"), None)
        for lang in strings.list_langs():
            await set_commands(get_object(lang, "commands"), lang)

    @dp.shutdown()
    async def on_shutdown() -> None:
        logger.info("Closing DB pool")
        await close_database_pool()
        logger.info("Aiogram: Bot shutdown")

    await dp.start_polling(bot)


def entrypoint() -> None:
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())


if __name__ == "__main__":
    entrypoint()
