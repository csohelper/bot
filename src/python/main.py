import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from .config import config
from .strings import strings
from aiogram.client.default import DefaultBotProperties

dp = Dispatcher()

@dp.message(Command("start"))
async def command_start_handler(message: Message) -> None:
    await message.answer(strings['commands'])


async def main() -> None:
    bot = Bot(
        token=config.telegram_token,
        default=DefaultBotProperties(parse_mode='HTML')
    )
    await dp.start_polling(bot)

def entrypoint():
    asyncio.run(main())

if __name__ == "__main__":
    entrypoint()