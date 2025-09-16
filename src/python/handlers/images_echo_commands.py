import asyncio
import os
from aiogram import Router, F
from ..storage.strings import get_string, get_object
from aiogram.types import Message
from aiogram.filters import Command, BaseFilter
from ..logger import logger
from aiogram.types import  FSInputFile, InputMediaPhoto, Message


router = Router()


cached_vost_file_id = None

@router.message(Command("vost"))
@router.message(lambda message: message.text and message.text.lower() in ["восточка"])
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

cached_bufet_file_id = None

@router.message(Command("bufet"))
@router.message(lambda message: message.text and message.text.lower() in ["буфет"])
async def command_bufet_handler(message: Message) -> None:
    await asyncio.sleep(1)
    global cached_bufet_file_id

    while True:
        if cached_bufet_file_id is None:
            image_path = "./src/res/images/cafe_bufet.jpg"
            sent: Message = await message.reply_photo(
                photo=FSInputFile(image_path),
                caption=get_string('echo_commands.cafe_bufet'),
                show_caption_above_media=True
            )
            if sent.photo:
                cached_bufet_file_id = sent.photo[-1].file_id
        else:
            try:
                await message.reply_photo(
                    photo=cached_bufet_file_id,
                    caption=get_string('echo_commands.cafe_bufet'),
                    show_caption_above_media=True
                )
            except Exception as e:
                logger.error(f"{e}")
                cached_bufet_file_id = None
                continue
        break


cached_linen_file_id = None

@router.message(Command("linen"))
@router.message(lambda message: message.text and message.text.lower() in ["обмен белья"])
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




cached_laundress_files_id = []

@router.message(Command("laundress"))
@router.message(lambda message: message.text and message.text.lower() in ["прачка", "прачечная", "прачка биля"])
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



cached_cards_files_id = []

@router.message(Command("cards"))
@router.message(lambda message: message.text and message.text.lower() in ["карты"])
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
                ) for x in sorted(os.listdir(cards_dir))
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


bad_words = get_object("bad_words")

def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("ё", "е")
    # убираем лишние символы, типа *, ., -, _
    clean = "".join(ch for ch in text if ch.isalnum() or ch.isspace())
    return clean

class BadWordFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return False
        if not message.text:
            return False

        text = normalize_text(message.text)

        for word in bad_words:
            if text == word:
                return True
        return False


cached_bad_words_file_id = None

@router.message(
    F.chat.type.in_(["group", "supergroup"]),
    BadWordFilter()
)
async def command_bad_words_handler(message: Message) -> None:
    global cached_bad_words_file_id

    while True:
        if cached_bad_words_file_id is None:
            image_path = "./src/res/images/bad_words.jpg"
            sent: Message = await message.reply_photo(photo=FSInputFile(image_path))
            if sent.photo:
                cached_bad_words_file_id = sent.photo[-1].file_id
        else:
            try:
                await message.reply_photo(photo=cached_bad_words_file_id)
            except Exception as e:
                logger.error(f"{e}")
                cached_bad_words_file_id = None
                continue
        break
