import asyncio
import os
import platform

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, Message, ReplyKeyboardRemove
from aiogram.types.link_preview_options import LinkPreviewOptions
from redis.asyncio import from_url
from aiohttp import ClientTimeout, TCPConnector  # Добавить эти импорты

from python import anecdote_poller, join_refuser
from python.handlers import echo_commands, kek_command, admin_commands, hype_collector
from python.handlers.services_handlers import add_service_commands, list_services_command, moderate_service, \
    join_service, my_services_command
from python.handlers import static_help
from python.storage import command_loader
from python.storage.cache import init_cache
from python.storage.command_loader import TelegramCommandsInfo, init_commands_info
from python.storage import config as config_module
from python.storage.database import open_database_pool, close_database_pool
from python.storage.repository import services_repository, users_repository, anecdotes_repository, hype_repository
from python.storage.strings import get_string, init_strings
from python.utils import await_and_run

bot: Bot
dp: Dispatcher

default_router = Router()


@default_router.message(F.chat.type == "private")
async def default_private_handler(message: Message):
    """Обработчик неизвестных команд в личных сообщениях."""
    await message.answer(
        get_string(message.from_user.language_code, "echo_commands.unknown"),
        reply_markup=ReplyKeyboardRemove()
    )


async def set_commands(info: TelegramCommandsInfo):
    """
    Установить команды бота в Telegram для конкретного языка.

    Args:
        info: Информация о командах для языка
    """
    commands = []
    for command_name in info.commands_list:
        commands.append(BotCommand(
            command=command_name.name,
            description=command_name.description,
        ))
    await bot.set_my_commands(
        commands=commands,
        language_code=info.lang,
    )


async def init_storage_systems():
    """
    Инициализировать все системы хранения данных.

    Вызывается перед запуском бота для загрузки:
    - Конфигурации приложения
    - Логгера (на основе конфига)
    - Системы локализации строк
    - Информации о командах
    - Кэша временных данных
    """
    # Используем print для начальных логов, так как logger еще не инициализирован
    print("Initializing storage systems...")

    try:
        # 1. Загрузка конфигурации (должна быть первой)
        print("Loading configuration...")
        config = await config_module.init_config()
        config_module.config = config

        # 2. Инициализация логгера на основе конфига
        print("Initializing logger...")
        from python.logger import init_logger
        init_logger(
            console_level=config.logger.console_level,
            file_level=config.logger.file_level,
            json_level=config.logger.json_level,
            aiogram_level=config.logger.aiogram_level,
            timezone=config.timezone,
            backup_limit=config.logger.backup_limit
        )

        # Теперь можно использовать logger
        from python.logger import logger
        logger.info("Logger initialized successfully")
        logger.info(f"Running on {platform.system()}")

        # 3. Загрузка системы локализации
        logger.debug("Loading localization system...")
        await init_strings()

        # 4. Загрузка информации о командах (зависит от strings)
        logger.debug("Loading commands info...")
        await init_commands_info()

        # 5. Загрузка кэша
        logger.debug("Loading cache...")
        await init_cache()

        logger.info("All storage systems initialized successfully")

    except Exception as e:
        print(f"ERROR: Failed to initialize storage systems: {e}")
        import traceback
        traceback.print_exc()
        raise


async def main() -> None:
    """
    Главная функция приложения.

    Инициализирует все компоненты бота и запускает polling.
    """
    global bot, dp

    # Инициализация систем хранения данных перед созданием бота
    await init_storage_systems()

    # Теперь logger и config инициализированы
    from python.logger import logger

    # Правильные таймауты для long polling
    timeout = ClientTimeout(
        total=None,  # Общий таймаут отключен для long polling
        connect=10,  # 10 секунд на подключение
        sock_connect=10,  # 10 секунд на socket connect
        sock_read=90  # 90 секунд на чтение (больше чем timeout long polling в getUpdates)
    )

    # Connector для управления соединениями
    connector = TCPConnector(
        limit=100,  # Общий лимит соединений
        limit_per_host=30,  # Лимит на хост
        ttl_dns_cache=300,  # Кэш DNS на 5 минут
        force_close=False,  # Переиспользовать соединения
        enable_cleanup_closed=True  # Автоматическая очистка закрытых соединений
    )

    # Создание сессии для подключения к Telegram API
    # Используем json параметр для передачи настроек в aiohttp ClientSession
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(config_module.config.telegram.server),
        timeout=timeout,
        json_loads=__import__('json').loads,  # Для совместимости
    )

    # Заменяем внутреннюю сессию на нашу с правильным connector
    import aiohttp
    session._session = aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        json_serialize=__import__('json').dumps
    )

    logger.info("AiohttpSession configured with long polling timeouts")

    # Инициализация бота
    bot = Bot(
        token=os.getenv("TELEGRAM_BOT_TOKEN", default=config_module.config.telegram.token),
        default=DefaultBotProperties(
            parse_mode=config_module.config.telegram.parse_mode,
            link_preview=LinkPreviewOptions(is_disabled=True),
            disable_notification=True
        ),
        session=session
    )

    # Выбор хранилища для FSM состояний (Redis или память)
    if config_module.config.redis_config.enabled:
        logger.info("Using Redis storage for FSM")
        redis = from_url(
            config_module.config.redis_config.url,
            decode_responses=config_module.config.redis_config.decode_responses
        )
        storage = RedisStorage(redis=redis)
    else:
        logger.info("Using Memory storage for FSM")
        storage = MemoryStorage()

    # Инициализация диспетчера
    dp = Dispatcher(storage=storage)

    # Подключение роутеров (порядок важен - default_router должен быть последним)
    dp.include_routers(
        echo_commands.router,
        kek_command.router,
        add_service_commands.router,
        list_services_command.router,
        moderate_service.router,
        admin_commands.router,
        join_service.router,
        hype_collector.router,
        static_help.router,
        default_router  # Must be in ending
    )

    @dp.startup()
    async def on_startup():
        """Хук, выполняемый при старте бота."""
        logger.info("Aiogram: starting bot")

        # Открытие пула соединений с базой данных
        await open_database_pool()
        logger.info("Database pool opened")

        # Инициализация обработчиков
        logger.info("Initializing handlers...")
        await kek_command.init(bot=bot)

        bot_username = str((await bot.get_me()).username)
        logger.info(f"Bot username: @{bot_username}")

        await add_service_commands.init(bot_username=bot_username, bot=bot)
        await list_services_command.init(bot_username=bot_username, bot=bot)
        await my_services_command.init(bot_username=bot_username, bot=bot)
        await moderate_service.init(bot_username=bot_username, bot=bot)
        await admin_commands.init(bot_username=bot_username, bot=bot)
        await join_refuser.init(bot=bot, storage=dp.storage)
        await join_service.init(bot=bot)
        await echo_commands.init(bot=bot)
        await hype_collector.init(bot_username=bot_username, bot=bot)
        await static_help.init(bot=bot)

        # Инициализация репозиториев базы данных
        logger.info("Initializing database repositories...")
        await services_repository.init_database_module()
        await anecdotes_repository.init_database_module()
        await users_repository.init_database_module()
        await hype_repository.init_database_module()

        # Запуск фоновых задач
        logger.info("Starting background tasks...")
        if config_module.config.anecdote.enabled:
            logger.info("Starting anecdote poller...")
            asyncio.create_task(await_and_run(10, anecdote_poller.anecdote_loop_check))

        if config_module.config.refuser.enabled:
            logger.info("Starting join refuser...")
            asyncio.create_task(await_and_run(10, join_refuser.refuser_loop_check))

        # Установка команд бота для всех языков
        logger.info("Setting bot commands for all languages...")
        commands_list = command_loader.get_telegram_commands_list()
        success_count = 0
        failed_count = 0

        for commands in commands_list:
            try:
                await set_commands(commands)
                success_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to set commands for language '{commands.lang}'", e)

        logger.info(f"Commands set: {success_count} succeeded, {failed_count} failed")

        # Регистрация эхо-команд
        logger.info("Registering echo command handlers...")
        from python.handlers.echo_commands import register_echo_handlers
        register_echo_handlers()

        # Обновление закрепленных справочных сообщений
        logger.info("Updating pinned help messages...")
        await static_help.on_start()

        logger.info("Starting deleting cycle")
        asyncio.create_task(echo_commands.delete_cycle())

        logger.info("Aiogram: bot started successfully")

    @dp.shutdown()
    async def on_shutdown() -> None:
        """Хук, выполняемый при остановке бота."""
        logger.info("Aiogram: shutting down bot")
        logger.info("Closing database pool...")
        await close_database_pool()
        logger.info("Aiogram: bot shutdown complete")

    # Запуск polling (бесконечный цикл обработки обновлений)
    logger.info("Starting polling...")
    await dp.start_polling(bot)


def entrypoint() -> None:
    """
    Точка входа в приложение.

    Настраивает event loop policy для Windows и запускает main().
    """
    # Для Windows нужна специальная политика event loop
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nApplication stopped by user (KeyboardInterrupt)")
    except Exception as e:
        print(f"FATAL ERROR: Application crashed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    entrypoint()
