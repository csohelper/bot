import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from python.handlers.services_handlers import add_service_commands, list_services_command, moderate_service
from python.handlers import echo_commands, images_echo_commands, kek_command, admin_commands
from python.storage import services_repository
from python.storage.config import config
from python.storage.strings import get_object
from aiogram.client.default import DefaultBotProperties
from python.storage.database import open_database_pool, close_database_pool
import platform
from python.logger import logger
from aiogram.types.link_preview_options import LinkPreviewOptions
from python import anecdote

bot: Bot
dp = Dispatcher()


@dp.startup()
async def on_startup(bot: Bot):
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
    await services_repository.init_database_module()

    await bot.set_my_commands(
        [
            BotCommand(command=x['command'], description=x['description']) for x in get_object("commands")
        ]
    )


@dp.shutdown()
async def on_shutdown(bot: Bot) -> None:
    logger.info("Closing DB pool")
    await close_database_pool()
    logger.info("Aiogram: Bot shutdown")


async def main() -> None:
    global bot
    bot = Bot(
        token=config.telegram.token,
        default=DefaultBotProperties(
            parse_mode=config.telegram.parse_mode,
            link_preview=LinkPreviewOptions(is_disabled=True),
            disable_notification=True
        )
    )
    if config.anecdote.enabled:
        asyncio.create_task(anecdote.loop_check())
    dp.include_routers(
        echo_commands.router,
        images_echo_commands.router,
        kek_command.router,
        add_service_commands.router,
        list_services_command.router,
        moderate_service.router,
        admin_commands.router
    )
    await dp.start_polling(bot)


def entrypoint() -> None:
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())


if __name__ == "__main__":
    entrypoint()
