import asyncio
from distutils.sysconfig import expand_makefile_vars
from gc import get_objects
import os
import random
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import BotCommand, FSInputFile, InputFile, InputFileUnion, InputMediaPhoto, MediaUnion, Message
from aiogram import F
from .config import config
from .strings import get_object, get_string, get_strings
from aiogram.client.default import DefaultBotProperties
from .database import open_database_pool, close_database_pool
import platform
from .logger import logger
from aiogram.types.link_preview_options import LinkPreviewOptions


dp = Dispatcher()

@dp.startup()
async def on_startup(bot: Bot):
    logger.info("Aiogram: Запуск бота...")
    await open_database_pool()
    logger.info("Aiogram: Бот успешно запущен.")

    await bot.set_my_commands(
        [
            BotCommand(command=x['command'], description=x['description']) for x in get_object("commands")
        ]
    )

@dp.shutdown()
async def on_shutdown(bot: Bot) -> None:
    logger.info("Aiogram: Остановка бота...")
    await close_database_pool()
    logger.info("Aiogram: Бот остановлен.")


@dp.message(Command("start", "help", "commands"))
@dp.message(lambda message: message.text and message.text.lower() in [
    "начать", "помощь", "хелп", "команды", "я долбаеб", "я долбоебка", "я долбаёб", "я долбоёбка", "я долбаебка", "я долбаёбка"
])
async def command_help_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.help'))


@dp.message(Command("index"))
@dp.message(lambda message: message.text and message.text.lower() in ["индекс"])
async def command_index_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.index'))


@dp.message(Command("address"))
@dp.message(lambda message: message.text and message.text.lower() in ["адрес"])
async def command_address_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.address'))


@dp.message(Command("director"))
@dp.message(lambda message: message.text and message.text.lower() in ["заведующий", "заведующая", "завед", "заведа"])
async def command_director_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.director'))


@dp.message(Command("jko"))
@dp.message(lambda message: message.text and message.text.lower() in ["жко"])
async def command_jko_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.jko'))


@dp.message(Command("hr"))
@dp.message(lambda message: message.text and message.text.lower() in ["отдел кадров"])
async def command_hr_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.hr'))


@dp.message(Command("polyclinic"))
@dp.message(lambda message: message.text and message.text.lower() in ["поликлиника"])
async def command_polyclinic_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.polyclinic'))


@dp.message(Command("library"))
@dp.message(lambda message: message.text and message.text.lower() in ["библиотека"])
async def command_library_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.library'))


@dp.message(Command("vost"))
@dp.message(lambda message: message.text and message.text.lower() in ["востока"])
async def command_vost_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.cafe_vost'))


@dp.message(Command("stolovka"))
@dp.message(lambda message: message.text and message.text.lower() in ["столовка"])
async def command_ulk_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.cafe_ulk'))


@dp.message(Command("services"))
@dp.message(lambda message: message.text and message.text.lower() in ["услуги"])
async def command_services_handler(message: Message) -> None:
    await message.reply(
        get_string('echo_commands.uslugi_stub')
    )


@dp.message(lambda message: message.text and message.text.lower() in ["мэи", "меи"])
async def command_mei_handler(message: Message) -> None:
    await message.reply(
        random.choice(
            get_strings('echo_commands.mei')
        )
    )


@dp.message(lambda message: message.text and message.text.lower() in ["мэишники", "меишники"])
async def command_meishniky_handler(message: Message) -> None:
    await message.reply(
        random.choice(
            get_strings('echo_commands.meishniky')
        )
    )


@dp.message(Command("shower"))
@dp.message(lambda message: message.text and message.text.lower() in ["душ"])
async def command_shower_handler(message: Message) -> None:
    await message.reply(
        get_string('echo_commands.shower')
    )


@dp.message(Command("kitchen"))
@dp.message(lambda message: message.text and message.text.lower() in ["кухня"])
async def command_kitchen_handler(message: Message) -> None:
    await message.reply(
        get_string('echo_commands.kitchen')
    )


@dp.message(Command("laundress"))
@dp.message(lambda message: message.text and message.text.lower() in ["прачка", "прачечная"])
async def command_laundress_handler(message: Message) -> None:
    await message.reply(
        get_string('echo_commands.laundress')
    )


@dp.message(Command("washing"))
@dp.message(lambda message: message.text and message.text.lower() in ["стиралка", "машинки"])
async def command_washing_handler(message: Message) -> None:
    await message.reply(
        get_string('echo_commands.washing')
    )

cached_cards_files_id = []

@dp.message(Command("cards"))
@dp.message(lambda message: message.text and message.text.lower() in ["карты"])
async def command_cards_handler(message: Message) -> None:
    """
    Отправляет пользователю изображения карт из src/res/images/cards.
    Если изображения уже были отправлены ранее, то использует кэшированные file_id.
    """

    global cached_cards_files_id

    if len(cached_cards_files_id) == 0:
        cards_dir = "./src/res/images/cards/"
        media=[
            InputMediaPhoto(
                media=FSInputFile(os.path.join(cards_dir, x))
            ) for x in os.listdir(cards_dir)
        ]
        media[-1].caption = get_string('echo_commands.cards')
        sent = await message.reply_media_group(media=media) # type: ignore[arg-type]
        
        for msg in sent:
            if msg.photo:
                largest_photo = msg.photo[-1]
                cached_cards_files_id.append(largest_photo.file_id)
    else:
        media = [
            InputMediaPhoto(
                media=file_id
            ) for file_id in cached_cards_files_id
        ]
        media[-1].caption = get_string('echo_commands.cards')
        await message.reply_media_group(media=media) # type: ignore[arg-type]
    

async def main() -> None:
    bot = Bot(
        token=config.telegram.token,
        default=DefaultBotProperties(
            parse_mode=config.telegram.parse_mode,
            link_preview = LinkPreviewOptions(is_disabled = True)
        )
    )
    await dp.start_polling(bot)

def entrypoint() -> None:
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

if __name__ == "__main__":
    entrypoint()