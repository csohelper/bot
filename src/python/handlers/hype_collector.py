from asyncio import sleep
from dataclasses import dataclass, asdict
from typing import Optional, List

from aiogram import Router, Bot, F, types
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardButton, KeyboardButton, ReplyKeyboardRemove, \
    User
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram_media_group import media_group_handler

from python.logger import logger
from python.storage.command_loader import get_all_triggers
from python.storage.config import config
from python.storage.repository import hype_repository
from python.storage.strings import get_string, get_string_variants
from python.utils import log_exception, download_photos, download_video

router = Router()

_bot_username: str
_bot: Bot


async def init(bot_username: str, bot: Bot):
    global _bot_username, _bot
    _bot_username = bot_username
    _bot = bot


@router.message(lambda message: message.text and message.text.lower() in get_all_triggers('hype_collector_greeting'))
async def greet(message: Message):
    try:
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
    except Exception as e:
        await message.reply(
            get_string(
                message.from_user.language_code,
                "exceptions.uncause",
                logger.error(e, message),
                config.chat_config.owner_username
            )
        )


class HypeStates(StatesGroup):
    waiting_start = State()
    sending_room = State()
    sending_contact = State()
    sending_description = State()
    sending_photos = State()
    sending_video = State()
    sending_confirm = State()


async def start_collector_command(message: Message, state: FSMContext):
    try:
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
    except Exception as e:
        await log_exception(e, message)


@router.message(
    HypeStates.waiting_start
)
async def on_accept(message: Message, state: FSMContext) -> None:
    try:
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
    except Exception as e:
        await log_exception(e, message)


@router.message(
    HypeStates.sending_room
)
async def on_room(message: Message, state: FSMContext):
    try:
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
                    'hype_collector.room_incorrect'
                ),
                reply_markup=ReplyKeyboardBuilder().row(
                    KeyboardButton(text=get_string(
                        message.from_user.language_code, "hype_collector.cancel_button"
                    )),
                ).as_markup(resize_keyboard=True, one_time_keyboard=False)
            )
        else:
            room = int(message.text)
            if room // 100 > 5 or room % 100 > 40:
                await message.reply(
                    get_string(
                        message.from_user.language_code,
                        'hype_collector.room_not_exists'
                    ),
                    reply_markup=ReplyKeyboardBuilder().row(
                        KeyboardButton(text=get_string(
                            message.from_user.language_code, "hype_collector.cancel_button"
                        )),
                    ).as_markup(resize_keyboard=True, one_time_keyboard=False)
                )
                return

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
    except Exception as e:
        await log_exception(e, message)


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
    """*Optional*. Contact's user identifier in Telegram. This number may have more than 32 significant bits and some 
    programming languages may have difficulty/silent defects in interpreting it. But it has at most 52 significant 
    bits, so a 64-bit integer or double-precision float type are safe for storing this identifier."""
    vcard: Optional[str] = None
    """*Optional*. Additional data about the contact in the form of a `vCard <https://en.wikipedia.org/wiki/VCard>`_"""


@router.message(
    HypeStates.sending_contact
)
async def on_contact(message: Message, state: FSMContext):
    try:
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
            await state.set_state(HypeStates.sending_description)
            await message.reply(
                get_string(
                    message.from_user.language_code,
                    'hype_collector.send_description'
                ),
                reply_markup=ReplyKeyboardBuilder().row(
                    KeyboardButton(text=get_string(
                        message.from_user.language_code, "hype_collector.skip_description"
                    )),
                    KeyboardButton(text=get_string(
                        message.from_user.language_code, "hype_collector.cancel_button"
                    )),
                ).as_markup(resize_keyboard=True, one_time_keyboard=False)
            )
    except Exception as e:
        await log_exception(e, message)


@router.message(HypeStates.sending_description)
async def on_description(message: Message, state: FSMContext):
    try:
        if message.text in get_string_variants("hype_collector.cancel_button"):
            await message.reply(
                get_string(
                    message.from_user.language_code,
                    'hype_collector.canceled'
                ),
                reply_markup=ReplyKeyboardRemove()
            )
            await state.clear()
        elif message.text in get_string_variants("hype_collector.skip_description"):
            await state.update_data(description=None)
        elif len(message.text) == 0:
            await message.reply(
                get_string(
                    message.from_user.language_code,
                    'hype_collector.description_empty'
                ),
                reply_markup=ReplyKeyboardBuilder().row(
                    KeyboardButton(text=get_string(
                        message.from_user.language_code, "hype_collector.skip_description"
                    )),
                    KeyboardButton(text=get_string(
                        message.from_user.language_code, "hype_collector.cancel_button"
                    )),
                ).as_markup(resize_keyboard=True, one_time_keyboard=False)
            )
        else:
            await state.update_data(description=message.text)

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
    except Exception as e:
        await log_exception(e, message)


@router.message(HypeStates.sending_photos, F.media_group_id, F.content_type.in_({'photo'}))
@media_group_handler
async def on_multiple_photos(messages: List[types.Message], state: FSMContext):
    await process_photos(
        messages[:3], state
    )


@router.message(HypeStates.sending_photos)
async def on_single_photo(message: Message, state: FSMContext):
    try:
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
    except Exception as e:
        await log_exception(e, message)


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
            fullname=from_user.full_name
        )


async def process_photos(messages: List[types.Message], state: FSMContext):
    try:
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
    except Exception as e:
        await messages[-1].reply(
            get_string(
                messages[-1].from_user.language_code,
                "exceptions.uncause",
                logger.error(e, messages[-1]),
                config.chat_config.owner_username
            )
        )


VIDEO_MAX_SIZE = 128


@router.message(HypeStates.sending_video)
async def process_video(message: Message, state: FSMContext):
    try:
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
    except Exception as e:
        await log_exception(e, message)


async def create_confirm(message: Message, state: FSMContext):
    try:
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
        description: str | None = await state.get_value("description")
        medias[-1].caption = get_string(
            message.from_user.language_code,
            'hype_collector.preview_caption',
            room=await state.get_value('room'),
            author=await parse_contact(message.from_user),
            description=description if description else get_string(
                message.from_user.language_code,
                "hype_collector.without_description"
            )
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
    except Exception as e:
        await log_exception(e, message)


async def video_callback_handler(percentage: int, wait_msg: Message, user_message: Message) -> None:
    try:
        """
        Coroutine to handle download progress updates by editing wait_msg or sending a new message if editing fails.
        """
        if percentage % 5 != 0 or percentage < 2:
            return
        text = get_string(
            user_message.from_user.language_code,
            "hype_collector.downloading_video_progress",
            progress=percentage
        )
        try:
            await wait_msg.edit_text(text)
        except TelegramRetryAfter:
            pass
        except TelegramBadRequest as e:
            logger.error(f"Cannot edit message: {e}")
    except Exception as e:
        await user_message.reply(
            get_string(
                user_message.from_user.language_code,
                "exceptions.uncause",
                logger.error(e, user_message),
                config.chat_config.owner_username
            )
        )


async def photo_callback_handler(download: int, count: int, wait_msg: Message, user_message: Message) -> None:
    """
    Coroutine to handle download progress updates by editing wait_msg or sending a new message if editing fails.
    """
    try:
        text = get_string(
            user_message.from_user.language_code,
            "hype_collector.downloading_photo_progress",
            download, count
        )
        try:
            await wait_msg.edit_text(text)
        except TelegramRetryAfter:
            pass
        except TelegramBadRequest as e:
            logger.error(f"Cannot edit message: {e}")
    except Exception as e:
        await user_message.reply(
            get_string(
                user_message.from_user.language_code,
                "exceptions.uncause",
                logger.error(e, user_message),
                config.chat_config.owner_username
            )
        )


@router.message(HypeStates.sending_confirm)
async def process_confirm(message: Message, state: FSMContext):
    try:
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
            await wait_msg.delete()
            wait_msg = await message.reply(
                get_string(
                    message.from_user.language_code,
                    "hype_collector.downloading_photo",
                )
            )

            photo_ids: list[str] = await state.get_value('photos')
            photo_files = await download_photos(
                _bot,
                photo_ids,
                lambda download, count: photo_callback_handler(download, count, wait_msg, message)
            )

            video_file = None
            video_id: str | None = await state.get_value('video')
            video_mime = await state.get_value('video_mime')
            if video_mime:
                await wait_msg.edit_text(
                    get_string(
                        message.from_user.language_code,
                        "hype_collector.downloading_video",
                    )
                )
                video_file = await download_video(
                    _bot,
                    video_id,
                    progress_callback=lambda progress: video_callback_handler(progress, wait_msg, message)
                )

            while True:
                try:
                    await wait_msg.edit_text(get_string(
                        message.from_user.language_code,
                        "hype_collector.processing",
                    ))
                    break
                except TelegramRetryAfter:
                    await sleep(1)

            contact = TelegramContact(**await state.get_value('contact'))
            description: str | None = await state.get_value('description')

            form_id = await hype_repository.insert_form(
                message.from_user.id,
                message.from_user.username,
                contact.phone_number,
                contact.vcard,
                message.from_user.full_name,
                photo_files,
                "image/jpeg",
                video_file,
                video_mime,
                description
            )

            medias: list[types.InputMediaPhoto | types.InputMediaVideo] = [
                types.InputMediaPhoto(media=file_id)
                for file_id in photo_ids
            ]
            if video_id:
                medias.insert(
                    0,
                    types.InputMediaVideo(
                        media=video_id
                    )
                )
            medias[-1].caption = get_string(
                message.from_user.language_code,
                'hype_collector.new_form',
                room=await state.get_value('room'),
                author=await parse_contact(message.from_user),
                id=form_id,
                description=description if description else get_string(
                    message.from_user.language_code,
                    'hype_collector.without_description',
                )
            )
            await _bot.send_media_group(
                config.chat_config.hype_chat_id,
                medias
            )

            while True:
                try:
                    await wait_msg.edit_text(
                        get_string(
                            message.from_user.language_code,
                            'hype_collector.sent',
                            room=await state.get_value('room'),
                            author=await parse_contact(message.from_user)
                        )
                    )
                    break
                except TelegramRetryAfter:
                    await sleep(1)
    except Exception as e:
        await log_exception(e, message)
