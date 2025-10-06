import base64
from dataclasses import dataclass, asdict
from string import capwords
from typing import Optional, List

from aiogram import Router, Bot, F, types
from aiogram.filters import state
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardRemove, \
    InputMediaPhoto, InputFile, User
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
        get_string(None, 'hype_collector.announce'),
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
    await process_photos(messages, state)


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


async def download_photos(file_ids: List[str]) -> list[str]:
    """
    Скачивает все фото из списка сообщений и возвращает список Base64 строк.
    """
    base64_photos = []

    for file_id in file_ids:
        # Скачиваем файл
        file = await _bot.get_file(file_id)
        file_bytes = await _bot.download_file(file.file_path)

        # Преобразуем в base64
        photo_b64 = base64.b64encode(file_bytes.read()).decode('utf-8')
        base64_photos.append(photo_b64)

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
    photos = [
        types.InputMediaPhoto(media=m.photo[-1].file_id)
        for m in messages
    ]
    photos[-1].caption = get_string(
        messages[-1].from_user.language_code,
        'hype_collector.preview_caption',
        room=await state.get_value('room'),
        author=await parse_contact(messages[-1].from_user)
    )
    await messages[-1].reply_media_group(photos)
    await messages[-1].answer(
        get_string(
            messages[-1].from_user.language_code,
            'hype_collector.send_confirm'
        ),
        reply_markup=ReplyKeyboardBuilder().row(
            KeyboardButton(text=get_string(
                messages[-1].from_user.language_code, "hype_collector.send_button"
            )),
            KeyboardButton(text=get_string(
                messages[-1].from_user.language_code, "hype_collector.cancel_button"
            ))
        ).as_markup(resize_keyboard=True, one_time_keyboard=False)
    )
    await state.set_state(HypeStates.sending_confirm)


@router.message(HypeStates.sending_confirm)
async def aaa(message: Message, state: FSMContext):
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
        file_ids: list[str] = await state.get_value('photos')
        download = await download_photos(file_ids)

        contact = TelegramContact(**await state.get_value('contact'))
        form_id = await hype_repository.insert_form(
            message.from_user.id,
            message.from_user.username,
            contact.phone_number,
            contact.vcard,
            message.from_user.full_name,
            download
        )

        photos = [
            types.InputMediaPhoto(media=file_id)
            for file_id in file_ids
        ]

        photos[-1].caption = get_string(
            message.from_user.language_code,
            'hype_collector.new_form',
            room=await state.get_value('room'),
            author=await parse_contact(message.from_user),
            id=form_id
        )
        await _bot.send_media_group(
            config.chat_config.hype_chat_id,
            photos
        )
        await message.reply(
            get_string(
                message.from_user.language_code,
                'hype_collector.sent',
                room=await state.get_value('room'),
                author=await parse_contact(message.from_user)
            ),
            reply_markup=ReplyKeyboardRemove()
        )
