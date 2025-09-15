import asyncio
from aiogram import Bot, Dispatcher, F, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, Message
from redis.asyncio import from_url

from python.handlers.services_handlers import add_service_commands, list_services_command, moderate_service
from python.handlers import echo_commands, images_echo_commands, kek_command, admin_commands, join_service
from python.storage import services_repository, users_repository
from python.storage.config import config
from python.storage.strings import get_object, get_string
from aiogram.client.default import DefaultBotProperties
from python.storage.database import open_database_pool, close_database_pool
import platform
from python.logger import logger
from aiogram.types.link_preview_options import LinkPreviewOptions
from python import anecdote

bot: Bot
dp: Dispatcher

default_router = Router()

@default_router.message(F.chat.type == "private")
async def default_private_handler(message: Message):
    await message.answer(get_string("echo_commands.unknown"))


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
    if config.anecdote.enabled:
        asyncio.create_task(anecdote.loop_check())
    dp.include_routers(
        echo_commands.router,
        images_echo_commands.router,
        kek_command.router,
        add_service_commands.router,
        list_services_command.router,
        moderate_service.router,
        admin_commands.router,
        join_service.router,
        default_router # Must be in ending
    )

    @dp.startup()
    async def on_startup():
        logger.info("Aiogram: starting bot")
        await open_database_pool()
        logger.info("Aiogram: bot started")
        await kek_command.init(
            bot=bot
        )
        bot_username = str((await bot.get_me()).username)
        await add_service_commands.init(bot_username=bot_username, bot=bot)
        await list_services_command.init(bot_username=bot_username, bot=bot)
        await moderate_service.init(bot_username=bot_username, bot=bot)
        await admin_commands.init(bot_username=bot_username, bot=bot)
        await join_service.init(bot=bot)
        await services_repository.init_database_module()
        await users_repository.init_database_module()

        await bot.set_my_commands(
            [
                BotCommand(command=x['command'], description=x['description']) for x in get_object("commands")
            ]
        )

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
