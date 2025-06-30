import asyncio
import datetime
from gc import get_objects
import os
import random
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import BotCommand, FSInputFile, InputFile, InputFileUnion, InputMediaPhoto, MediaUnion, Message
from aiogram import F
from dynaconf.validator_conditions import cont
from .config import config
from .strings import get_object, get_string, get_strings
from aiogram.client.default import DefaultBotProperties
from .database import open_database_pool, close_database_pool
import platform
from .logger import logger
from aiogram.types.link_preview_options import LinkPreviewOptions
from . import utils


dp = Dispatcher()

@dp.startup()
async def on_startup(bot: Bot):
    logger.info("Aiogram: starting bot")
    await open_database_pool()
    logger.info("Aiogram: bot started")

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


@dp.message(Command("start", "help", "commands", "comands"))
@dp.message(lambda message: message.text and message.text.lower() in [
    "начать", "помощь", "хелп", "команды", "комманды", "список", "помоги", "я долбаеб", "я долбоебка", "я долбаёб", "я долбоёбка", "я долбаебка", "я долбаёбка"
])
async def command_help_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.help'))


@dp.message(Command("index"))
@dp.message(lambda message: message.text and message.text.lower() in ["индекс"])
async def command_index_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.index'))


@dp.message(Command("address"))
@dp.message(lambda message: message.text and message.text.lower() in ["адрес", "адресс", "адресочек"])
async def command_address_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.address'))


@dp.message(Command("director"))
@dp.message(lambda message: message.text and message.text.lower() in ["заведующий", "заведующая", "завед", "заведа"])
async def command_director_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.director'))


@dp.message(Command("commandant"))
@dp.message(lambda message: message.text and message.text.lower() in ["коменда", "комендант", "командант", "командантка", "комменда", "коммендант", "коммандант", "коммандантка"])
async def command_commandant_handler(message: Message) -> None:
    await message.reply(
        get_string('echo_commands.commandant')
    )

@dp.message(Command("jko"))
@dp.message(lambda message: message.text and message.text.lower() in ["жко", "жк", "жилищно коммунальный", "жилищно коммунальный отдел", "жилищно-коммунальный отдел"])
async def command_jko_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.jko'))


@dp.message(Command("ed"))
@dp.message(lambda message: message.text and message.text.lower() in ["ед", "единый деканат", "деканат"])
async def command_ed_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.ed'))


@dp.message(Command("hr"))
@dp.message(lambda message: message.text and message.text.lower() in ["отдел кадров"])
async def command_hr_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.hr'))


@dp.message(Command("soft"))
@dp.message(lambda message: message.text and message.text.lower() in ["софт", "программы", "программное обеспечение", "ПО"])
async def command_soft_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.soft'))


@dp.message(Command("library"))
@dp.message(lambda message: message.text and message.text.lower() in ["библиотека"])
async def command_library_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.library'))

cached_vost_file_id = None

@dp.message(Command("vost"))
@dp.message(lambda message: message.text and message.text.lower() in ["восточка"])
async def command_vost_handler(message: Message) -> None:
    global cached_vost_file_id

    while True:
        if cached_vost_file_id is None:
            image_path = "./src/res/images/cafe_vost.jpg"
            sent: Message = await message.reply_photo(
                photo=FSInputFile(image_path),
                caption=get_string('echo_commands.cafe_vost'),
                show_caption_above_media=True
            )
            if sent.photo:
                cached_vost_file_id = sent.photo[-1].file_id
        else:
            try:
                await message.reply_photo(
                    photo=cached_vost_file_id,
                    caption=get_string('echo_commands.cafe_vost'),
                    show_caption_above_media=True
                )
            except Exception as e:
                logger.error(f"{e}")
                cached_vost_file_id = None
                continue
        break

cached_linen_file_id = None

@dp.message(Command("linen"))
@dp.message(lambda message: message.text and message.text.lower() in ["обмен белья"])
async def command_linen_handler(message: Message) -> None:
    global cached_linen_file_id

    while True:
        if cached_linen_file_id is None:
            image_path = "./src/res/images/linen.jpg"
            sent: Message = await message.reply_photo(
                photo=FSInputFile(image_path),
                caption=get_string('echo_commands.linen'),
                show_caption_above_media=True
            )
            if sent.photo:
                cached_linen_file_id = sent.photo[-1].file_id
        else:
            try:
                await message.reply_photo(
                    photo=cached_linen_file_id,
                    caption=get_string('echo_commands.linen'),
                    show_caption_above_media=True
                )
            except Exception as e:
                logger.error(f"{e}")
                cached_linen_file_id = None
                continue
        break


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


@dp.message(Command("mei"))
@dp.message(lambda message: message.text and message.text.lower() in ["мэи", "меи"])
async def command_mei_handler(message: Message) -> None:
    await message.reply(
        random.choice(
            get_strings('echo_commands.mei')
        )
    )


@dp.message(Command("meishniky"))
@dp.message(lambda message: message.text and message.text.lower() in ["мэишники", "меишники"])
async def command_meishniky_handler(message: Message) -> None:
    await message.reply(
        random.choice(
            get_strings('echo_commands.meishniky')
        )
    )

@dp.message(Command("mai"))
@dp.message(lambda message: message.text and message.text.lower() in ["маи"])
async def command_mai_handler(message: Message) -> None:
    await message.reply(
        random.choice(
            get_strings('echo_commands.mai')
        )
    )


@dp.message(Command("maishniki"))
@dp.message(lambda message: message.text and message.text.lower() in ["маишники", "маёвцы"])
async def command_maishniky_handler(message: Message) -> None:
    await message.reply(
        random.choice(
            get_strings('echo_commands.maishniky')
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


cached_laundress_files_id = []

@dp.message(Command("laundress"))
@dp.message(lambda message: message.text and message.text.lower() in ["прачка", "прачечная", "прачка биля"])
async def command_laundress_handler(message: Message) -> None:
    """
    Отправляет пользователю изображения прачки из src/res/images/laundress.
    Если изображения уже были отправлены ранее, то использует кэшированные file_id.
    """

    global cached_laundress_files_id

    while True:
        if len(cached_laundress_files_id) == 0:
            laundress_dir = "./src/res/images/laundress/"
            media=[
                InputMediaPhoto(
                    media=FSInputFile(os.path.join(laundress_dir, x)),
                    show_caption_above_media=True
                ) for x in os.listdir(laundress_dir)
            ]
            media[0].caption = get_string('echo_commands.laundress')
            sent = await message.reply_media_group(media=media) # type: ignore[arg-type]
            
            for msg in sent:
                if msg.photo:
                    largest_photo = msg.photo[-1]
                    cached_laundress_files_id.append(largest_photo.file_id)
        else:
            try:
                media = [
                    InputMediaPhoto(
                        media=file_id,
                        show_caption_above_media=True
                    ) for file_id in cached_laundress_files_id
                ]
                media[0].caption = get_string('echo_commands.laundress')
                await message.reply_media_group(media=media) # type: ignore[arg-type]
            except Exception as e:
                logger.error(f"{e}")
                cached_laundress_files_id = []
                continue
        break



# @dp.message(Command("washing"))
# @dp.message(lambda message: message.text and message.text.lower() in ["стиралка", "машинки"])
# async def command_washing_handler(message: Message) -> None:
#     await message.reply(
#         get_string('echo_commands.washing')
#     )

cached_cards_files_id = []

@dp.message(Command("cards"))
@dp.message(lambda message: message.text and message.text.lower() in ["карты"])
async def command_cards_handler(message: Message) -> None:
    """
    Отправляет пользователю изображения карт из src/res/images/cards.
    Если изображения уже были отправлены ранее, то использует кэшированные file_id.
    """

    global cached_cards_files_id

    while True:
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
            try:
                media = [
                    InputMediaPhoto(
                        media=file_id
                    ) for file_id in cached_cards_files_id
                ]
                media[-1].caption = get_string('echo_commands.cards')
                await message.reply_media_group(media=media) # type: ignore[arg-type]
            except Exception as e:
                logger.error(f"{e}")
                cached_cards_files_id = []
                continue
        break

@dp.message(Command("week"))
@dp.message(lambda message: message.text and message.text.lower() in ["неделя"])
async def command_week_handler(message: Message) -> None:
    week_number = utils.get_week_number(datetime.datetime.now())
    await message.reply(
        get_string(
            'echo_commands.week', 
            get_strings('echo_commands.week_types_up_down')[week_number % 2],
            get_strings('echo_commands.week_types_even')[week_number % 2],
            week_number
        )
    )


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