import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import F
from .config import config
from .strings import get_string
from aiogram.client.default import DefaultBotProperties
from .database import open_database_pool, close_database_pool
import platform
from .logger import logger


dp = Dispatcher()

@dp.startup()
async def on_startup():
    logger.info("Aiogram: Запуск бота...")
    await open_database_pool()
    logger.info("Aiogram: Бот успешно запущен.")


@dp.shutdown()
async def on_shutdown():
    logger.info("Aiogram: Остановка бота...")
    await close_database_pool()
    logger.info("Aiogram: Бот остановлен.")


@dp.message(Command("start"))
@dp.message(lambda message: message.text and message.text.lower() in [
    "начать", "помощь", "хелп", "команды", "я долбаеб", "я долбоебка", "я долбаёб", "я долбоёбка", 
])
async def command_start_handler(message: Message) -> None:
    await message.answer(get_string('echo_commands.help'))


async def main() -> None:
    bot = Bot(
        token=config.telegram.token,
        default=DefaultBotProperties(parse_mode=config.telegram.parse_mode)
    )
    await dp.start_polling(bot)

def entrypoint():
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

if __name__ == "__main__":
    entrypoint()