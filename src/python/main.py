import asyncio
import platform

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, Message, ReplyKeyboardRemove, CallbackQuery, ChatJoinRequest
from aiogram.types.link_preview_options import LinkPreviewOptions
from redis.asyncio import from_url

from python import anecdote_poller, join_refuser
from python.handlers import echo_commands, kek_command, admin_commands, hype_collector
from python.handlers.services_handlers import add_service_commands, list_services_command, moderate_service, \
    join_service, my_services_command
from python.logger import logger
from python.storage import command_loader
from python.storage.command_loader import TelegramCommandsInfo
from python.storage.config import config
from python.storage.database import open_database_pool, close_database_pool
from python.storage.repository import services_repository, users_repository, anecdotes_repository, hype_repository
from python.storage.strings import get_string
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


async def set_commands(info: TelegramCommandsInfo):
    commands = []
    for l in info.commands_list:
        commands.append(BotCommand(
            command=l.name,
            description=l.description,
        ))
    await bot.set_my_commands(
        commands=commands,
        language_code=info.lang,
    )


async def main() -> None:
    global bot, dp

    session = AiohttpSession(
        api=TelegramAPIServer.from_base(config.telegram.local_server)
    )
    bot = Bot(
        token=config.telegram.token,
        default=DefaultBotProperties(
            parse_mode=config.telegram.parse_mode,
            link_preview=LinkPreviewOptions(is_disabled=True),
            disable_notification=True
        ),
        session=session
    )
    if config.redis_config.enabled:
        redis = from_url(config.redis_config.url, decode_responses=config.redis_config.decode_responses)
        storage = RedisStorage(redis=redis)
    else:
        storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_routers(
        echo_commands.router,
        kek_command.router,
        add_service_commands.router,
        list_services_command.router,
        moderate_service.router,
        admin_commands.router,
        join_service.router,
        hype_collector.router,
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
        await my_services_command.init(bot_username=bot_username, bot=bot)
        await moderate_service.init(bot_username=bot_username, bot=bot)
        await admin_commands.init(bot_username=bot_username, bot=bot)
        await join_refuser.init(bot=bot, storage=dp.storage)
        await join_service.init(bot=bot)
        await hype_collector.init(bot_username=bot_username, bot=bot)
        await services_repository.init_database_module()
        await anecdotes_repository.init_database_module()
        await users_repository.init_database_module()
        await hype_repository.init_database_module()
        if config.anecdote.enabled:
            asyncio.create_task(await_and_run(10, anecdote_poller.anecdote_loop_check))
        if config.refuser.enabled:
            asyncio.create_task(await_and_run(10, join_refuser.refuser_loop_check))

        commands_list = command_loader.get_telegram_commands_list()
        # print(json.dumps([asdict(cmd) for cmd in commands_list], indent=4, ensure_ascii=False))
        for commands in commands_list:
            try:
                await set_commands(commands)
            except Exception as e:
                logger.error(e)

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


async def log_exception(e: Exception, original: Message | CallbackQuery | ChatJoinRequest) -> None:
    code = logger.error(e, original)
    await original.reply(
        get_string(
            original.from_user.language_code,
            "exceptions.uncause",
            code,
            config.chat_config.owner
        )
    )
    await original.bot.send_message(
        config.chat_config.admin_chat_id,
        get_string(
            config.chat_config.admin_lang,
            "exceptions.debug",
            code=code, exc=str(e),
            userid=original.from_user.id,
            username=original.from_user.username,
            fullname=original.from_user.full_name,
        ),
        message_thread_id=config.chat_config.admin_debug_topic
    )


if __name__ == "__main__":
    entrypoint()
