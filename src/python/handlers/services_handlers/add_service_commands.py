import asyncio
import base64
import io
from dataclasses import replace

from aiogram import Bot, Router
from aiogram import types
from aiogram.filters import Command, StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Message, \
    FSInputFile, BufferedInputFile, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from python import utils
from python.handlers.services_handlers import moderate_service
from python.storage.repository import services_repository
from python.storage.repository.services_repository import Service
from python.storage.strings import get_string
from python.utils import log_exception

_bot_username: str
_bot: Bot


async def init(bot_username: str, bot: Bot):
    global _bot_username, _bot
    _bot_username = bot_username
    _bot = bot


router = Router()


class AddServiceStates(StatesGroup):
    choosing_name_state = State()
    choosing_description_state = State()
    choosing_cost_state = State()
    choosing_cost_per_state = State()
    choosing_picture_state = State()


@router.message(StateFilter(None), Command("addservice"))
async def on_addservice(message: Message, state: FSMContext, lang=None) -> None:
    try:
        if lang is None:
            lang = message.from_user.language_code
        if message.chat.type != 'private':
            await message.answer(
                text=get_string(lang, 'services.add_command.not_private').strip(),
                reply_markup=InlineKeyboardBuilder().row(
                    InlineKeyboardButton(
                        text=get_string(lang, 'services.add_command.goto_pm'),
                        url=await create_start_link(_bot, 'addservice', encode=True)
                    )
                ).as_markup()
            )
            return
        await message.reply(
            text=get_string(lang, 'services.add_command.greeting'),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text=get_string(lang, 'services.add_command.cancel_button'))
            ).as_markup(resize_keyboard=True, one_time_keyboard=False)
        )
        await state.set_state(AddServiceStates.choosing_name_state)
    except Exception as e:
        await log_exception(e, message, state=state)


@router.message(
    AddServiceStates.choosing_name_state
)
async def on_name_chosen(message: Message, state: FSMContext) -> None:
    try:
        if message.text == get_string(message.from_user.language_code, 'services.add_command.cancel_button'):
            await message.reply(
                text=get_string(message.from_user.language_code, 'services.add_command.cancel_message'),
                reply_markup=ReplyKeyboardRemove()
            )
            await state.clear()
            return
        if not message.text or not 4 <= len(message.text) <= 25:
            await message.reply(
                text=get_string(message.from_user.language_code, 'services.add_command.incorrect_name')
            )
            return

        await state.update_data(
            name=message.text
        )
        await message.reply(
            text=get_string(message.from_user.language_code, 'services.add_command.choose_description'),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(
                    text=get_string(message.from_user.language_code, 'services.add_command.without_description')),
                KeyboardButton(text=get_string(message.from_user.language_code, 'services.add_command.cancel_button'))
            ).as_markup(resize_keyboard=True, one_time_keyboard=False)
        )
        await state.set_state(AddServiceStates.choosing_description_state)
    except Exception as e:
        await log_exception(e, message, state=state)


@router.message(
    AddServiceStates.choosing_description_state
)
async def on_description_chosen(message: Message, state: FSMContext) -> None:
    try:
        if message.text == get_string(message.from_user.language_code, 'services.add_command.cancel_button'):
            await message.reply(
                text=get_string(message.from_user.language_code, 'services.add_command.cancel_message'),
                reply_markup=ReplyKeyboardRemove()
            )
            await state.clear()
            return
        if message.text is None or message.text.strip() == '':
            await message.reply(get_string(message.from_user.language_code, 'services.add_command.empty_description'))
            return
        elif message.text == get_string(message.from_user.language_code, 'services.add_command.without_description'):
            await state.update_data(
                description=None
            )
        else:
            await state.update_data(
                description=message.text
            )
        await message.reply(
            text=get_string(message.from_user.language_code, 'services.add_command.choose_cost'),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text=get_string(message.from_user.language_code, 'services.add_command.cancel_button'))
            ).as_markup(resize_keyboard=True, one_time_keyboard=False)
        )
        await state.set_state(AddServiceStates.choosing_cost_state)
    except Exception as e:
        await log_exception(e, message, state=state)


@router.message(
    AddServiceStates.choosing_cost_state
)
async def on_cost_chosen(message: Message, state: FSMContext) -> None:
    try:
        if message.text == get_string(message.from_user.language_code, 'services.add_command.cancel_button'):
            await message.reply(
                text=get_string(message.from_user.language_code, 'services.add_command.cancel_message'),
                reply_markup=ReplyKeyboardRemove()
            )
            await state.clear()
            return

        if not message.text or not message.text.isdigit() or int(message.text) <= 0:
            await message.reply(
                text=get_string(message.from_user.language_code, 'services.add_command.cost_not_int')
            )
            return

        if len(message.text) > 6:
            await message.reply(
                text=get_string(message.from_user.language_code, 'services.add_command.cost_too_big')
            )
            return

        await state.update_data(
            cost=int(message.text)
        )
        await message.reply(
            text=get_string(message.from_user.language_code, 'services.add_command.choose_cost_per'),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text=get_string(message.from_user.language_code, 'services.add_command.cancel_button'))
            ).as_markup(resize_keyboard=True, one_time_keyboard=False)
        )
        await state.set_state(AddServiceStates.choosing_cost_per_state)
    except Exception as e:
        await log_exception(e, message, state=state)


@router.message(
    AddServiceStates.choosing_cost_per_state
)
async def on_cost_per_chosen(message: Message, state: FSMContext) -> None:
    try:
        if message.text == get_string(message.from_user.language_code, 'services.add_command.cancel_button'):
            await message.reply(
                text=get_string(message.from_user.language_code, 'services.add_command.cancel_message'),
                reply_markup=ReplyKeyboardRemove()
            )
            await state.clear()
            return

        if not message.text or not (1 <= len(message.text) <= 6):
            await message.reply(
                text=get_string(
                    message.from_user.language_code, 'services.add_command.incorrect_input.cost_per_incorrect',
                    1, 6
                )
            )
            return

        await state.update_data(
            cost_per=message.text
        )
        await message.reply(
            text=get_string(message.from_user.language_code, 'services.add_command.choose_picture'),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(
                    text=get_string(message.from_user.language_code, 'services.add_command.without_picture')),
                KeyboardButton(text=get_string(message.from_user.language_code, 'services.add_command.cancel_button'))
            ).as_markup(resize_keyboard=True, one_time_keyboard=False)
        )
        await state.set_state(AddServiceStates.choosing_picture_state)
    except Exception as e:
        await log_exception(e, message, state=state)


@router.message(
    AddServiceStates.choosing_picture_state
)
async def on_picture_chosen(message: Message, state: FSMContext) -> None:
    try:
        if message.text == get_string(message.from_user.language_code, 'services.add_command.cancel_button'):
            await message.reply(
                text=get_string(message.from_user.language_code, 'services.add_command.cancel_message'),
                reply_markup=ReplyKeyboardRemove()
            )
            await state.clear()
            return

        if message.text == get_string(message.from_user.language_code, 'services.add_command.without_picture'):
            await state.update_data(
                image=None
            )
            await process_create_service(message, state)
            await state.clear()
            return

        if not message.photo:
            await message.reply(
                get_string(message.from_user.language_code, "services.add_command.not_photo_and_empty")
            )
            return

        largest_photo = message.photo[-1]
        photo_base64: str = (await utils.download_photos(
            _bot,
            [largest_photo.file_id]
        ))[0]

        await state.update_data(
            image=photo_base64
        )

        await process_create_service(message, state)
        await state.clear()
    except Exception as e:
        await log_exception(e, message, state=state)


async def process_create_service(message: Message, state: FSMContext) -> None:
    try:
        data = await state.get_data()
        if data['image']:
            image_bytes = base64.b64decode(data['image'])
            image_stream = io.BytesIO(image_bytes)
            media = BufferedInputFile(image_stream.read(), filename=f"preview.jpg")
        else:
            media = FSInputFile('./src/res/images/services/no_image.jpg')

        if not message.from_user:
            return

        service = services_repository.Service(
            id=None,
            directory='/',
            name=data['name'],
            cost=data['cost'],
            cost_per=data['cost_per'],
            description=data['cost_per'],
            owner=message.from_user.id,
            image=data['image'],
            status='moderation'
        )

        service = replace(
            service,
            id=await services_repository.create_service(service)
        )

        desc = data['description']
        caption = get_string(
            message.from_user.language_code,
            'services.add_command.preview',
            data['name'],
            data['cost'], data['cost_per'],
            desc if desc else get_string(message.from_user.language_code, 'services.service_no_description')
        )

        keyboard = InlineKeyboardBuilder().row(InlineKeyboardButton(
            text=get_string(message.from_user.language_code, "services.add_command.edit_buttons.edit_name"),
            callback_data='a'
        )).row(InlineKeyboardButton(
            text=get_string(message.from_user.language_code, "services.add_command.edit_buttons.edit_description"),
            callback_data='a'
        )).row(InlineKeyboardButton(
            text=get_string(message.from_user.language_code, "services.add_command.edit_buttons.edit_cost"),
            callback_data='a'
        )).row(InlineKeyboardButton(
            text=get_string(message.from_user.language_code, "services.add_command.edit_buttons.edit_cost_per"),
            callback_data='a'
        )).row(InlineKeyboardButton(
            text=get_string(message.from_user.language_code, "services.add_command.edit_buttons.edit_image"),
            callback_data='a'
        )).row(InlineKeyboardButton(
            text=get_string(message.from_user.language_code, "services.add_command.edit_buttons.publish"),
            callback_data='a'
        )).as_markup()

        reply = await message.reply_photo(
            photo=media,
            caption=caption,
            reply_markup=keyboard,
        )

        update_keyboard = InlineKeyboardBuilder().row(InlineKeyboardButton(
            text=get_string(message.from_user.language_code, "services.add_command.edit_buttons.edit_name"),
            callback_data=EditServiceCallbackFactory(
                original_msg=reply.message_id,
                service_id=service.id or 0,
                action='change_name'
            ).pack()
        )).row(InlineKeyboardButton(
            text=get_string(message.from_user.language_code, "services.add_command.edit_buttons.edit_description"),
            callback_data=EditServiceCallbackFactory(
                original_msg=reply.message_id,
                service_id=service.id or 0,
                action='change_description'
            ).pack()
        )).row(InlineKeyboardButton(
            text=get_string(message.from_user.language_code, "services.add_command.edit_buttons.edit_cost"),
            callback_data=EditServiceCallbackFactory(
                original_msg=reply.message_id,
                service_id=service.id or 0,
                action='change_cost'
            ).pack()
        )).row(InlineKeyboardButton(
            text=get_string(message.from_user.language_code, "services.add_command.edit_buttons.edit_cost_per"),
            callback_data=EditServiceCallbackFactory(
                original_msg=reply.message_id,
                service_id=service.id or 0,
                action='change_cost_per'
            ).pack()
        )).row(InlineKeyboardButton(
            text=get_string(message.from_user.language_code, "services.add_command.edit_buttons.edit_image"),
            callback_data=EditServiceCallbackFactory(
                original_msg=reply.message_id,
                service_id=service.id or 0,
                action='change_image'
            ).pack()
        )).row(InlineKeyboardButton(
            text=get_string(message.from_user.language_code, "services.add_command.edit_buttons.publish"),
            callback_data=EditServiceCallbackFactory(
                original_msg=reply.message_id,
                service_id=service.id or 0,
                action='publish'
            ).pack()
        ))
        await reply.edit_reply_markup(
            reply_markup=update_keyboard.as_markup()
        )
    except Exception as e:
        await log_exception(e, message, state=state)


class EditServiceCallbackFactory(CallbackData, prefix="editsrvc"):
    original_msg: int
    service_id: int
    action: str


@router.callback_query(EditServiceCallbackFactory.filter())
async def callbacks_edit_service(
        callback: types.CallbackQuery,
        callback_data: EditServiceCallbackFactory,
        state: FSMContext
) -> None:
    try:
        if not callback.message:
            return
        match callback_data.action:
            case 'change_name':
                await state.set_state(EditServiceStates.edit_name_state)
                reply = await callback.message.reply(
                    text=get_string(callback.from_user.language_code, "services.add_command.edit_name"))
                await state.update_data(callback_data=callback_data.pack(), reply=reply.message_id)
            case 'change_description':
                await state.set_state(EditServiceStates.edit_description_state)
                reply = await callback.message.reply(
                    text=get_string(callback.from_user.language_code, "services.add_command.edit_description"))
                await state.update_data(callback_data=callback_data.pack(), reply=reply.message_id)
            case 'change_cost':
                await state.set_state(EditServiceStates.edit_cost_state)
                reply = await callback.message.reply(
                    text=get_string(callback.from_user.language_code, "services.add_command.edit_cost"))
                await state.update_data(callback_data=callback_data.pack(), reply=reply.message_id)
            case 'change_cost_per':
                await state.set_state(EditServiceStates.edit_cost_per_state)
                reply = await callback.message.reply(
                    text=get_string(callback.from_user.language_code, "services.add_command.edit_cost_per"))
                await state.update_data(callback_data=callback_data.pack(), reply=reply.message_id)
            case "change_image":
                await state.set_state(EditServiceStates.edit_picture_state)
                reply = await callback.message.reply(
                    text=get_string(callback.from_user.language_code, "services.add_command.edit_picture"))
                await state.update_data(callback_data=callback_data.pack(), reply=reply.message_id)
            case "publish":
                service = await services_repository.find_service(service_id=callback_data.service_id)
                await _bot.edit_message_caption(
                    chat_id=callback.message.chat.id,
                    message_id=callback_data.original_msg,
                    caption=get_string(
                        callback.from_user.language_code,
                        'services.add_command.sent_to_moderation',
                        service.name,
                        service.cost, service.cost_per,
                        service.description if service.description else get_string(
                            callback.from_user.language_code,
                            'services.service_no_description'
                        )
                    )
                )
                await _bot.send_message(
                    chat_id=callback.message.chat.id,
                    reply_to_message_id=callback_data.original_msg,
                    text=get_string(
                        callback.from_user.language_code,
                        'services.add_command.wait_for_moderation'
                    ),
                    reply_markup=ReplyKeyboardRemove()
                )
                await moderate_service.send_to_moderation(
                    service, callback.from_user.full_name,
                    callback.from_user.language_code
                )

        await callback.answer()
    except Exception as e:
        await log_exception(e, callback, state=state)


class EditServiceStates(StatesGroup):
    edit_name_state = State()
    edit_description_state = State()
    edit_cost_state = State()
    edit_cost_per_state = State()
    edit_picture_state = State()


def create_preview_keyboard(original_msg: int, service_id: int, lang) -> InlineKeyboardMarkup:
    return InlineKeyboardBuilder().row(InlineKeyboardButton(
        text=get_string(lang, "services.add_command.edit_buttons.edit_name"),
        callback_data=EditServiceCallbackFactory(
            original_msg=original_msg,
            service_id=service_id,
            action='change_name'
        ).pack()
    )).row(InlineKeyboardButton(
        text=get_string(lang, "services.add_command.edit_buttons.edit_description"),
        callback_data=EditServiceCallbackFactory(
            original_msg=original_msg,
            service_id=service_id,
            action='change_description'
        ).pack()
    )).row(InlineKeyboardButton(
        text=get_string(lang, "services.add_command.edit_buttons.edit_cost"),
        callback_data=EditServiceCallbackFactory(
            original_msg=original_msg,
            service_id=service_id,
            action='change_cost'
        ).pack()
    )).row(InlineKeyboardButton(
        text=get_string(lang, "services.add_command.edit_buttons.edit_cost_per"),
        callback_data=EditServiceCallbackFactory(
            original_msg=original_msg,
            service_id=service_id,
            action='change_cost_per'
        ).pack()
    )).row(InlineKeyboardButton(
        text=get_string(lang, "services.add_command.edit_buttons.edit_image"),
        callback_data=EditServiceCallbackFactory(
            original_msg=original_msg,
            service_id=service_id,
            action='change_image'
        ).pack()
    )).row(InlineKeyboardButton(
        text=get_string(lang, "services.add_command.edit_buttons.publish"),
        callback_data=EditServiceCallbackFactory(
            original_msg=original_msg,
            service_id=service_id,
            action='publish'
        ).pack()
    )).as_markup()


async def update_preview_text(
        lang: str | None, chat: int, preview_message: int,
        service: Service, update_image: bool = False
):
    if update_image:
        if service.image:
            image_bytes = base64.b64decode(service.image)
            image_stream = io.BytesIO(image_bytes)
            media = BufferedInputFile(image_stream.read(), filename=f"{service.id}.jpg")
        else:
            media = FSInputFile('./src/res/images/services/no_image.jpg')
        await _bot.edit_message_media(
            media=InputMediaPhoto(
                media=media,
                caption=get_string(
                    lang,
                    'services.add_command.preview',
                    service.name,
                    service.cost, service.cost_per,
                    service.description if service.description else get_string(
                        lang, 'services.service_no_description'
                    )
                ),
            ),
            chat_id=chat,
            message_id=preview_message,
            reply_markup=create_preview_keyboard(preview_message, service.id, lang)
        )
    else:
        await _bot.edit_message_caption(
            chat_id=chat,
            message_id=preview_message,
            caption=get_string(
                lang,
                'services.add_command.preview',
                service.name,
                service.cost, service.cost_per,
                service.description if service.description else get_string(
                    lang, 'services.service_no_description'
                )
            ),
            reply_markup=create_preview_keyboard(preview_message, service.id, lang)
        )


@router.message(
    EditServiceStates.edit_name_state
)
async def on_name_edit(message: Message, state: FSMContext) -> None:
    try:
        if message.text is None or message.text.strip() == '':
            reply = await message.reply(get_string(
                message.from_user.language_code,
                "services.add_command.incorrect_input.name"
            ))
            await asyncio.sleep(3)
            await reply.delete()
            await message.delete()
            return
        callback_data: EditServiceCallbackFactory = EditServiceCallbackFactory.unpack(
            await state.get_value("callback_data")
        )
        reply_message: int = await state.get_value("reply")
        await _bot.delete_message(message.chat.id, reply_message)
        await _bot.delete_message(message.chat.id, message.message_id)
        service = await services_repository.update_service_fields(callback_data.service_id, name=message.text)
        if service:
            await update_preview_text(message.from_user.language_code, message.chat.id, callback_data.original_msg,
                                      service)
        await state.clear()
    except Exception as e:
        await log_exception(e, message, state=state)


@router.message(
    EditServiceStates.edit_description_state
)
async def on_description_edit(message: Message, state: FSMContext) -> None:
    try:
        if message.text is None or message.text.strip() == '':
            reply = await message.reply(get_string(
                message.from_user.language_code,
                "services.add_command.incorrect_input.description"
            ))
            await asyncio.sleep(3)
            await reply.delete()
            await message.delete()
            return
        elif message.text == '/empty':
            description = None
        else:
            description = message.text.strip()

        callback_data: EditServiceCallbackFactory = EditServiceCallbackFactory.unpack(
            await state.get_value("callback_data")
        )
        reply_message: int = await state.get_value("reply")
        await _bot.delete_message(message.chat.id, reply_message)
        await _bot.delete_message(message.chat.id, message.message_id)
        service = await services_repository.update_service_fields(callback_data.service_id, description=description)
        if service:
            await update_preview_text(message.from_user.language_code, message.chat.id, callback_data.original_msg,
                                      service)
        await state.clear()
    except Exception as e:
        await log_exception(e, message, state=state)


@router.message(
    EditServiceStates.edit_cost_state
)
async def on_cost_edit(message: Message, state: FSMContext) -> None:
    try:
        if not message.text or not message.text.isdigit() or int(message.text) <= 0:
            reply = await message.reply(
                text=get_string(message.from_user.language_code, 'services.add_command.incorrect_input.cost_not_int')
            )
            await asyncio.sleep(3)
            await reply.delete()
            await message.delete()
            return
        elif len(message.text) > 6:
            reply = await message.reply(
                text=get_string(message.from_user.language_code, 'services.add_command.incorrect_input.cost_too_big')
            )
            await asyncio.sleep(3)
            await reply.delete()
            await message.delete()
            return

        callback_data: EditServiceCallbackFactory = EditServiceCallbackFactory.unpack(
            await state.get_value("callback_data")
        )
        reply_message: int = await state.get_value("reply")
        await _bot.delete_message(message.chat.id, reply_message)
        await _bot.delete_message(message.chat.id, message.message_id)
        service = await services_repository.update_service_fields(callback_data.service_id, cost=int(message.text))
        if service:
            await update_preview_text(message.from_user.language_code, message.chat.id, callback_data.original_msg,
                                      service)
        await state.clear()
    except Exception as e:
        await log_exception(e, message, state=state)


@router.message(
    EditServiceStates.edit_cost_per_state
)
async def on_cost_per_edit(message: Message, state: FSMContext) -> None:
    try:
        if not message.text or not (1 <= len(message.text) <= 6):
            reply = await message.reply(
                text=get_string(
                    message.from_user.language_code, 'services.add_command.incorrect_input.cost_per_incorrect',
                    1, 6
                )
            )
            await asyncio.sleep(3)
            await reply.delete()
            await message.delete()
            return

        callback_data: EditServiceCallbackFactory = EditServiceCallbackFactory.unpack(
            await state.get_value("callback_data")
        )
        reply_message: int = await state.get_value("reply")
        await _bot.delete_message(message.chat.id, reply_message)
        await _bot.delete_message(message.chat.id, message.message_id)
        service = await services_repository.update_service_fields(callback_data.service_id, cost_per=message.text)
        if service:
            await update_preview_text(message.from_user.language_code, message.chat.id, callback_data.original_msg,
                                      service)
        await state.clear()
    except Exception as e:
        await log_exception(e, message, state=state)


@router.message(
    EditServiceStates.edit_picture_state
)
async def on_picture_edit(message: Message, state: FSMContext) -> None:
    try:
        if message.text == '/empty':
            await state.update_data(
                image=None
            )
            await process_create_service(message, state)
            await state.clear()
            return

        if not message.photo:
            reply = await message.reply(get_string(
                message.from_user.language_code, "services.add_command.incorrect_input.not_photo_and_empty"
            ))
            await asyncio.sleep(3)
            await reply.delete()
            await message.delete()
            return

        largest_photo = message.photo[-1]

        photo_base64 = (await utils.download_photos(
            _bot,
            [largest_photo.file_id]
        ))[0]

        callback_data: EditServiceCallbackFactory = EditServiceCallbackFactory.unpack(
            await state.get_value("callback_data")
        )
        reply_message: int = await state.get_value("reply")
        service = await services_repository.update_service_fields(callback_data.service_id, image=photo_base64)
        if service:
            await update_preview_text(message.from_user.language_code, message.chat.id, callback_data.original_msg,
                                      service,
                                      True)
        await _bot.delete_message(message.chat.id, reply_message)
        await _bot.delete_message(message.chat.id, message.message_id)
        await state.clear()
    except Exception as e:
        await log_exception(e, message, state=state)
