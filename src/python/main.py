import asyncio
import datetime
from gc import get_objects
import os
import random
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.types import BotCommand, ChatPermissions, FSInputFile, InputFile, InputFileUnion, InputMediaPhoto, MediaUnion, Message
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
from . import anecdote

bot: Bot
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
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.help'))


@dp.message(Command("index"))
@dp.message(lambda message: message.text and message.text.lower() in ["индекс"])
async def command_index_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.index'))


kek_last_use = {}


@dp.message(Command("kek"))
@dp.message(lambda message: message.text and message.text.lower() in ["kek", "кек"])
async def command_anecdote_handler(message: Message) -> None:
    if message.chat.type not in ['group', 'supergroup']:
        await message.reply(get_string(
            'echo_commands.kek.only_group'
        ))
        return

    global kek_last_use
    if message.chat.id in kek_last_use:
        last_use_chat = kek_last_use[message.chat.id]
    else:
        last_use_chat = datetime.datetime(2000, 1, 1, 0, 0)

    if not message.from_user:
        return

    delta: datetime.timedelta = datetime.datetime.now() - last_use_chat
    if delta < datetime.timedelta(seconds=30):
        reply = await message.reply(get_string(
            'echo_commands.kek.too_many', 
            message.from_user.full_name,
            30 - int(delta.total_seconds())
        ))
        await asyncio.sleep(5)
        try:
            await message.delete()
        except Exception as e:
            logger.error(f"Failed delete user message {message}: {e}")
        try:
            await reply.delete()
        except Exception as e:
            logger.error(f"Failed delete reply message {reply}: {e}")
        return

    kek_last_use[message.chat.id] = datetime.datetime.now()

    if random.random() < 0.05:
        ban_time = random.randint(1, 30)
        reply = await message.reply(get_string(
            'echo_commands.kek.ban',
            message.from_user.full_name,
            ban_time
        ))
        try:
            await bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.datetime.now() + datetime.timedelta(minutes=ban_time)
            )
        except TelegramBadRequest:
            await reply.edit_text(get_string(
                'echo_commands.kek.ban_admin',
                message.from_user.full_name,
                ban_time
            ))
        return

    for i in range(100):
        if i % 5 == 0:
            try:
                await bot.send_chat_action(
                    chat_id=message.chat.id,
                    action='typing',
                    message_thread_id=message.message_thread_id
                )
            except TelegramRetryAfter:
                logger.warning("Telegram action type status restricted by flood control")
        try:
            _, modified = await anecdote.generate_anekdot()
            if modified:
                await message.reply(get_string(
                    'echo_commands.kek.anecdote',
                    modified
                ))
                return
        except Exception as e:
            logger.error(f"Failed to generate anecdote with exc {e}. Retrying...")
    await message.reply(get_string(
        'echo_commands.kek.not_found'
    ))


@dp.message(Command("address"))
@dp.message(lambda message: message.text and message.text.lower() in ["адрес", "адресс", "адресочек"])
async def command_address_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.address'))


@dp.message(Command("director"))
@dp.message(lambda message: message.text and message.text.lower() in ["заведующий", "заведующая", "завед", "заведа"])
async def command_director_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.director'))


@dp.message(Command("commandant"))
@dp.message(lambda message: message.text and message.text.lower() in ["коменда", "комендант", "командант", "командантка", "комменда", "коммендант", "коммандант", "коммандантка"])
async def command_commandant_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(
        get_string('echo_commands.commandant')
    )

@dp.message(Command("jko"))
@dp.message(lambda message: message.text and message.text.lower() in ["жко", "жк", "жилищно коммунальный", "жилищно коммунальный отдел", "жилищно-коммунальный отдел"])
async def command_jko_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.jko'))


@dp.message(Command("ed"))
@dp.message(lambda message: message.text and message.text.lower() in ["ед", "единый деканат", "деканат"])
async def command_ed_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.ed'))


@dp.message(Command("hr"))
@dp.message(lambda message: message.text and message.text.lower() in ["отдел кадров"])
async def command_hr_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.hr'))


@dp.message(Command("soft"))
@dp.message(lambda message: message.text and message.text.lower() in ["софт", "программы", "программное обеспечение", "ПО"])
async def command_soft_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.soft'))


@dp.message(Command("sosat"))
@dp.message(lambda message: message.text and message.text.lower() in ["сосать", "долбаёб", "шлюха", "мразь", "сука"])
async def command_sosat_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.sosat'))


@dp.message(Command("library"))
@dp.message(lambda message: message.text and message.text.lower() in ["библиотека"])
async def command_library_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.library'))

cached_vost_file_id = None

@dp.message(Command("vost"))
@dp.message(lambda message: message.text and message.text.lower() in ["восточка"])
async def command_vost_handler(message: Message) -> None:
    await asyncio.sleep(1)
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
    await asyncio.sleep(1)
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
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.cafe_ulk'))


@dp.message(Command("services"))
@dp.message(lambda message: message.text and message.text.lower() in ["услуги"])
async def command_services_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(
        get_string('echo_commands.uslugi_stub')
    )


@dp.message(Command("mei"))
@dp.message(lambda message: message.text and message.text.lower() in ["мэи", "меи"])
async def command_mei_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(
        random.choice(
            get_strings('echo_commands.mei')
        )
    )


@dp.message(Command("meishniky"))
@dp.message(lambda message: message.text and message.text.lower() in ["мэишники", "меишники"])
async def command_meishniky_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(
        random.choice(
            get_strings('echo_commands.meishniky')
        )
    )

@dp.message(Command("mai"))
@dp.message(lambda message: message.text and message.text.lower() in ["маи"])
async def command_mai_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(
        random.choice(
            get_strings('echo_commands.mai')
        )
    )


@dp.message(Command("maishniki"))
@dp.message(lambda message: message.text and message.text.lower() in ["маишники", "маёвцы"])
async def command_maishniky_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(
        random.choice(
            get_strings('echo_commands.maishniky')
        )
    )


@dp.message(Command("shower"))
@dp.message(lambda message: message.text and message.text.lower() in ["душ"])
async def command_shower_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(
        get_string('echo_commands.shower')
    )


@dp.message(Command("kitchen"))
@dp.message(lambda message: message.text and message.text.lower() in ["кухня"])
async def command_kitchen_handler(message: Message) -> None:
    await asyncio.sleep(1)
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

    await asyncio.sleep(1)
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

    await asyncio.sleep(1)
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
    await asyncio.sleep(1)
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
    global bot
    bot = Bot(
        token=config.telegram.token,
        default=DefaultBotProperties(
            parse_mode=config.telegram.parse_mode,
            link_preview = LinkPreviewOptions(is_disabled = True),
            disable_notification = True
        )
    )
    await dp.start_polling(bot)

def entrypoint() -> None:
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

if __name__ == "__main__":
    entrypoint()