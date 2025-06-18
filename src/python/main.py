import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from . import config

dp = Dispatcher()

@dp.message(Command("start"))
async def command_start_handler(message: Message) -> None:
    await message.answer("Hello! I'm a bot created with aiogram.")


async def main() -> None:
    print(config.config.telegram_token)
    bot = Bot(token=config.config.telegram_token)
    await dp.start_polling(bot)

def entrypoint():
    asyncio.run(main())

if __name__ == "__main__":
    entrypoint()