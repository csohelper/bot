import base64
import mimetypes
from dataclasses import dataclass, asdict
from io import BytesIO
from string import capwords
from typing import Optional, List

import aiofiles
import aiohttp
from aiogram import Router, Bot, F, types
from aiogram.filters import state
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardRemove, \
    InputMediaPhoto, InputFile, User, File
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram_media_group import media_group_handler

from python.storage.command_loader import get_all_triggers
from python.storage.config import config
from python.storage.repository import hype_repository
from python.storage.strings import get_string, get_string_variants

router = Router()

_bot_username: str
_bot: Bot


async def init(bot_username: str, bot: Bot):
    global _bot_username, _bot
    _bot_username = bot_username
    _bot = bot


@router.message(lambda message: message.text and message.text.lower() in get_all_triggers('hype_collector_greeting'))
async def greet(message: Message):
    await message.answer(
        get_string(
            None, 'hype_collector.announce',
            date='25.10.25'
        ),
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(
                text=get_string(None, 'hype_collector.start'),
                url=await create_start_link(
                    _bot,
                    get_string(None, "payloads.hype_collector_start"),
                    encode=True
                )
            )
        ).as_markup()
    )
    await message.delete()


class HypeStates(StatesGroup):
    waiting_start = State()
    sending_room = State()
    sending_contact = State()
    sending_photos = State()
    sending_video = State()
    sending_confirm = State()


async def start_collector_command(message: Message, state: FSMContext):
    await message.reply(
        get_string(
            message.from_user.language_code,
            'hype_collector.greeting'
        ),
        reply_markup=ReplyKeyboardBuilder().row(
            KeyboardButton(text=get_string(
                message.from_user.language_code, "hype_collector.greeting_button"
            )),
            KeyboardButton(text=get_string(
                message.from_user.language_code, "hype_collector.cancel_button"
            )),
        ).as_markup(resize_keyboard=True, one_time_keyboard=False)
    )
    await state.set_state(HypeStates.waiting_start)


@router.message(
    HypeStates.waiting_start
)
async def on_accept(message: Message, state: FSMContext) -> None:
    if message.text in get_string_variants("hype_collector.greeting_button"):
        await state.set_state(HypeStates.sending_room)
        await message.reply(
            get_string(
                message.from_user.language_code,
                'hype_collector.send_room'
            ),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text=get_string(
                    message.from_user.language_code, "hype_collector.cancel_button"
                )),
            ).as_markup(resize_keyboard=True, one_time_keyboard=False)
        )
    elif message.text in get_string_variants("hype_collector.cancel_button"):
        await message.reply(
            get_string(
                message.from_user.language_code,
                'hype_collector.canceled'
            ),
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
    else:
        await message.reply(get_string(
            message.from_user.language_code,
            'hype_collector.greeting'
        ))


@router.message(
    HypeStates.sending_room
)
async def on_room(message: Message, state: FSMContext):
    if message.text in get_string_variants("hype_collector.cancel_button"):
        await message.reply(
            get_string(
                message.from_user.language_code,
                'hype_collector.canceled'
            ),
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
    elif not message.text or len(message.text) != 3 or not message.text.isdigit() or int(message.text) < 0:
        await message.reply(
            get_string(
                message.from_user.language_code,
                'hype_collector.send_room'
            ),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text=get_string(
                    message.from_user.language_code, "hype_collector.cancel_button"
                )),
            ).as_markup(resize_keyboard=True, one_time_keyboard=False)
        )
    else:
        room = int(message.text)
        await state.update_data(room=room)
        await state.set_state(HypeStates.sending_contact)
        await message.reply(
            get_string(
                message.from_user.language_code,
                'hype_collector.send_contact'
            ),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(
                    text=get_string(
                        message.from_user.language_code, "hype_collector.send_contact_button"
                    ),
                    request_contact=True
                ),
                KeyboardButton(text=get_string(
                    message.from_user.language_code, "hype_collector.cancel_button"
                )),
            ).as_markup(resize_keyboard=True, one_time_keyboard=False)
        )


@dataclass(frozen=True)
class TelegramContact:
    """
    This object represents a phone contact.

    Source: https://core.telegram.org/bots/api#contact

    Copy of aiogram type
    """

    phone_number: str
    """Contact's phone number"""
    first_name: str
    """Contact's first name"""
    last_name: Optional[str] = None
    """*Optional*. Contact's last name"""
    user_id: Optional[int] = None
    """*Optional*. Contact's user identifier in Telegram. This number may have more than 32 significant bits and some programming languages may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits, so a 64-bit integer or double-precision float type are safe for storing this identifier."""
    vcard: Optional[str] = None
    """*Optional*. Additional data about the contact in the form of a `vCard <https://en.wikipedia.org/wiki/VCard>`_"""


@router.message(
    HypeStates.sending_contact
)
async def on_contact(message: Message, state: FSMContext):
    if message.text in get_string_variants("hype_collector.cancel_button"):
        await message.reply(
            get_string(
                message.from_user.language_code,
                'hype_collector.canceled'
            ),
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
    elif not message.contact:
        await message.reply(
            get_string(
                message.from_user.language_code,
                'hype_collector.send_contact'
            ),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(
                    text=get_string(
                        message.from_user.language_code, "hype_collector.send_contact_button"
                    ),
                    request_contact=True
                ),
                KeyboardButton(text=get_string(
                    message.from_user.language_code, "hype_collector.cancel_button"
                )),
            ).as_markup(resize_keyboard=True, one_time_keyboard=False)
        )
    else:
        await state.update_data(
            contact=asdict(TelegramContact(**message.contact.__dict__))
        )
        await state.set_state(HypeStates.sending_photos)
        await message.reply(
            get_string(
                message.from_user.language_code,
                'hype_collector.send_photos'
            ),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text=get_string(
                    message.from_user.language_code, "hype_collector.cancel_button"
                )),
            ).as_markup(resize_keyboard=True, one_time_keyboard=False)
        )


@router.message(HypeStates.sending_photos, F.media_group_id, F.content_type.in_({'photo'}))
@media_group_handler
async def on_multiple_photos(messages: List[types.Message], state: FSMContext):
    await process_photos(
        messages[:3], state
    )


@router.message(HypeStates.sending_photos)
async def on_single_photo(message: Message, state: FSMContext):
    if message.text in get_string_variants("hype_collector.cancel_button"):
        await message.reply(
            get_string(
                message.from_user.language_code,
                'hype_collector.canceled'
            ),
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
    elif not message.photo:
        await message.reply(
            get_string(
                message.from_user.language_code,
                'hype_collector.send_photos'
            ),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text=get_string(
                    message.from_user.language_code, "hype_collector.cancel_button"
                )),
            ).as_markup(resize_keyboard=True, one_time_keyboard=False)
        )
    else:
        await process_photos([message], state)


async def download_photos(file_ids: List[str]) -> List[str]:
    """
    Скачивает все фото или видео из списка file_ids через nginx и возвращает список Base64-строк.
    """
    base64_photos = []

    async with aiohttp.ClientSession() as session:
        for file_id in file_ids:
            try:
                # Получаем информацию о файле через nginx
                file: File = await _bot.get_file(file_id)

                # Обрезаем префикс /var/lib/telegram-bot-api/
                relative_path = file.file_path.lstrip('/var/lib/telegram-bot-api/')

                # Формируем URL для скачивания
                download_url = f"{config.telegram.download_server}/file/{relative_path}"

                # Скачиваем файл
                async with session.get(download_url) as response:
                    if response.status != 200:
                        raise Exception(f"Ошибка скачивания: {response.status}, URL: {download_url}")
                    file_bytes = await response.read()

                # Преобразуем в Base64
                photo_b64 = base64.b64encode(file_bytes).decode('utf-8')
                base64_photos.append(photo_b64)

            except Exception as e:
                print(f"Ошибка при скачивании file_id={file_id}: {str(e)}")
                continue  # Пропускаем ошибочный файл

    return base64_photos


async def parse_contact(from_user: User):
    if from_user.username:
        return get_string(
            from_user.language_code,
            'hype_collector.contact.default',
            username=from_user.username
        )
    else:
        return get_string(
            from_user.language_code,
            'hype_collector.contact.nousername',
            userid=from_user.id,
            fullname=from_user.fullname
        )


async def process_photos(messages: List[types.Message], state: FSMContext):
    await state.update_data(photos=[
        x.photo[-1].file_id for x in messages
    ])
    await messages[-1].reply(
        get_string(
            messages[-1].from_user.language_code,
            "hype_collector.send_video",
            max_size=VIDEO_MAX_SIZE
        ),
        reply_markup=ReplyKeyboardBuilder().row(
            KeyboardButton(
                text=get_string(
                    messages[-1].from_user.language_code,
                    "hype_collector.skip_video"
                )
            ),
            KeyboardButton(
                text=get_string(
                    messages[-1].from_user.language_code,
                    "hype_collector.cancel_button"
                )
            ),
        ).as_markup(resize_keyboard=True, one_time_keyboard=False)
    )
    await state.set_state(HypeStates.sending_video)


VIDEO_MAX_SIZE = 128

from io import BytesIO, BufferedIOBase
import mimetypes
import base64


async def download_video(file_id: str | None) -> str | None:
    """
    Скачивает видео через nginx (local Telegram Bot API) и возвращает Base64 и MIME-тип.
    """
    # URL nginx (порт 8082 из вашего docker-compose)
    # Токен бота (хардкод для примера, лучше брать из конфига)

    # Получаем информацию о файле
    if not file_id:
        return None

    file_info: File = await _bot.get_file(file_id)

    # file_path: /var/lib/telegram-bot-api/<token>/videos/file_0.mp4
    # Обрезаем префикс, чтобы получить относительный путь: <token>/videos/file_0.mp4
    relative_path = file_info.file_path.lstrip('/var/lib/telegram-bot-api/')

    # Формируем URL для скачивания через nginx
    download_url = f"{config.telegram.download_server}/file/{relative_path}"
    print(download_url)

    # Скачиваем файл через aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(download_url) as response:
            if response.status != 200:
                raise Exception(f"Ошибка скачивания: {response.status}, URL: {download_url}")
            data_bytes = await response.read()

    # Кодируем в Base64
    return base64.b64encode(data_bytes).decode("utf-8")


@router.message(HypeStates.sending_video)
async def process_video(message: Message, state: FSMContext):
    if message.text in get_string_variants("hype_collector.cancel_button"):
        await message.reply(
            get_string(
                message.from_user.language_code,
                'hype_collector.canceled'
            ),
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
    elif message.text in get_string_variants("hype_collector.skip_video"):
        await state.update_data(video=None)
    elif not message.video:
        await message.reply(
            get_string(
                message.from_user.language_code,
                "hype_collector.send_video",
                max_size=VIDEO_MAX_SIZE
            ),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(
                    text=get_string(
                        message.from_user.language_code,
                        "hype_collector.skip_video"
                    )
                ),
                KeyboardButton(
                    text=get_string(
                        message.from_user.language_code,
                        "hype_collector.cancel_button"
                    )
                ),
            ).as_markup(resize_keyboard=True, one_time_keyboard=False)
        )
        return
    elif message.video.file_size / 1048576 > VIDEO_MAX_SIZE:
        await message.reply(
            get_string(
                message.from_user.language_code,
                "hype_collector.big_video",
                max_size=VIDEO_MAX_SIZE
            ),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(
                    text=get_string(
                        message.from_user.language_code,
                        "hype_collector.skip_video"
                    )
                ),
                KeyboardButton(
                    text=get_string(
                        message.from_user.language_code,
                        "hype_collector.cancel_button"
                    )
                ),
            ).as_markup(resize_keyboard=True, one_time_keyboard=False)
        )
        return
    else:
        await state.update_data(video_mime=message.video.mime_type)
        await state.update_data(video=message.video.file_id)
    await state.set_state(HypeStates.sending_confirm)
    await create_confirm(message, state)


async def create_confirm(message: Message, state: FSMContext):
    photo_ids: list[str] = await state.get_value("photos")
    medias: list[types.InputMediaPhoto | types.InputMediaVideo] = [
        types.InputMediaPhoto(media=file_id)
        for file_id in photo_ids
    ]

    video = await state.get_value("video")
    if video:
        medias.insert(
            0,
            types.InputMediaVideo(
                media=video
            )
        )
    medias[-1].caption = get_string(
        message.from_user.language_code,
        'hype_collector.preview_caption',
        room=await state.get_value('room'),
        author=await parse_contact(message.from_user)
    )
    await message.reply_media_group(medias)
    await message.answer(
        get_string(
            message.from_user.language_code,
            'hype_collector.send_confirm'
        ),
        reply_markup=ReplyKeyboardBuilder().row(
            KeyboardButton(text=get_string(
                message.from_user.language_code, "hype_collector.send_button"
            )),
            KeyboardButton(text=get_string(
                message.from_user.language_code, "hype_collector.cancel_button"
            ))
        ).as_markup(resize_keyboard=True, one_time_keyboard=False)
    )


@router.message(HypeStates.sending_confirm)
async def process_confirm(message: Message, state: FSMContext):
    if message.text in get_string_variants("hype_collector.cancel_button"):
        await message.reply(
            get_string(
                message.from_user.language_code,
                'hype_collector.canceled'
            ),
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
    elif message.text not in get_string_variants("hype_collector.send_button"):
        await message.reply(
            get_string(
                message.from_user.language_code,
                'hype_collector.sent_confirm',
                room=await state.get_value('room'),
                author=await parse_contact(message.from_user)
            ),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text=get_string(
                    message.from_user.language_code, "hype_collector.send_button"
                )),
                KeyboardButton(text=get_string(
                    message.from_user.language_code, "hype_collector.cancel_button"
                ))
            ).as_markup(resize_keyboard=True, one_time_keyboard=False)
        )
    else:
        wait_msg = await message.reply(
            get_string(
                message.from_user.language_code,
                "hype_collector.processing",
            ),
            reply_markup=ReplyKeyboardRemove()
        )
        print(await state.get_value('video'))
        video = await download_video(await state.get_value('video'))
        video_mime = await state.get_value('video_mime')

        file_ids: list[str] = await state.get_value('photos')
        files = await download_photos(file_ids)

        contact = TelegramContact(**await state.get_value('contact'))
        form_id = await hype_repository.insert_form(
            message.from_user.id,
            message.from_user.username,
            contact.phone_number,
            contact.vcard,
            message.from_user.full_name,
            files,
            "image/jpeg",
            video,
            video_mime
        )
        await wait_msg.delete()

        medias: list[types.InputMediaPhoto | types.InputMediaVideo] = [
            types.InputMediaPhoto(media=file_id)
            for file_id in file_ids
        ]
        if video:
            medias.insert(
                0,
                types.InputMediaVideo(
                    media=video
                )
            )
        medias[-1].caption = get_string(
            message.from_user.language_code,
            'hype_collector.new_form',
            room=await state.get_value('room'),
            author=await parse_contact(message.from_user),
            id=form_id
        )
        await _bot.send_media_group(
            config.chat_config.hype_chat_id,
            medias
        )
        await message.reply(
            get_string(
                message.from_user.language_code,
                'hype_collector.sent',
                room=await state.get_value('room'),
                author=await parse_contact(message.from_user)
            )
        )
