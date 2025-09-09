import base64
import io
from unittest import case

from aiogram import Bot, Router, types
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import FSInputFile, BufferedInputFile, InlineKeyboardButton, Message, InlineKeyboardMarkup, \
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from python.storage import services_repository
from python.storage.config import config
from python.storage.services_repository import Service
from python.storage.strings import get_string

_bot_username: str
_bot: Bot


async def init(bot_username: str, bot: Bot):
    global _bot_username, _bot
    _bot_username = bot_username
    _bot = bot


router = Router()


class ModerateCallbackFactory(CallbackData, prefix="moderate"):
    service_id: int
    author_name: str
    action: str
    original_msg: int


def create_markup(service_id: int, author_name: str, original_msg: int) -> InlineKeyboardMarkup:
    return InlineKeyboardBuilder().row(InlineKeyboardButton(
        text='📂Установить категорию',
        callback_data=ModerateCallbackFactory(
            service_id=service_id,
            author_name=author_name,
            action='set_category',
            original_msg=original_msg
        ).pack()
    )).row(InlineKeyboardButton(
        text='🚫Отклонить',
        callback_data=ModerateCallbackFactory(
            service_id=service_id,
            author_name=author_name,
            action='refuse',
            original_msg=original_msg
        ).pack()
    )).row(InlineKeyboardButton(
        text='✅Одобрить',
        callback_data=ModerateCallbackFactory(
            service_id=service_id,
            author_name=author_name,
            action='accept',
            original_msg=original_msg
        ).pack()
    )).as_markup()


def create_caption(service: Service, author_name: str) -> str:
    status = "unknown"
    match service.status:
        case "moderation":
            status = get_string("services.moderation.status.moderation")
        case "published":
            status = get_string("services.moderation.status.accept")
        case "rejected":
            status = get_string("services.moderation.status.reject")
    if service.directory != "/":
        category_footer = get_string(
            "services.moderation.category",
            service.directory.replace("/", " → ")
        )
    else:
        category_footer = ""

    return "\n".join((get_string(
        "services.moderation.preview",
        status,
        service.name, service.cost,
        service.cost_per, service.description,
        service.owner, author_name
    ), category_footer)).strip()


async def send_to_moderation(service: Service, sender_name: str) -> None:
    if service.image:
        image_bytes = base64.b64decode(service.image)
        image_stream = io.BytesIO(image_bytes)
        media = BufferedInputFile(image_stream.read(), filename=f"preview.jpg")
    else:
        media = FSInputFile('./src/res/images/empty_service.jpg')

    reply = await _bot.send_photo(
        chat_id=config.chat_config.admin_chat_id,
        photo=media,
        caption=create_caption(service, sender_name),
        reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(
            text='📂Установить категорию',
            callback_data='.'
        )).row(InlineKeyboardButton(
            text='🚫Отклонить',
            callback_data='.'
        )).row(InlineKeyboardButton(
            text='✅Одобрить',
            callback_data='.'
        )).as_markup()
    )

    await reply.edit_reply_markup(reply_markup=create_markup(service.id, sender_name, reply.message_id))


class ModerateStates(StatesGroup):
    choosing_category = State()
    refusing = State()
    accept = State()


@router.callback_query(ModerateCallbackFactory.filter())
async def callbacks_moderate_buttons(
        callback: types.CallbackQuery,
        callback_data: ModerateCallbackFactory,
        state: FSMContext
) -> None:
    if not callback.message:
        return
    match callback_data.action:
        case 'set_category':
            await callback.message.answer(
                get_string("services.moderation.setting_category"),
                reply_markup=category_markup()
            )
            await state.update_data(callback_data=callback_data)
            await state.set_state(ModerateStates.choosing_category)
    match callback_data.action:
        case 'refuse':
            await callback.message.answer(
                text=get_string("services.moderation.refuse"),
                reply_markup=reject_markup()
            )
            await state.update_data(callback_data=callback_data)
            await state.set_state(ModerateStates.refusing)
    match callback_data.action:
        case 'accept':
            await callback.message.answer(
                text=get_string("services.moderation.accepting"),
                reply_markup=accept_markup()
            )
            await state.update_data(callback_data=callback_data)
            await state.set_state(ModerateStates.accept)


def category_markup() -> ReplyKeyboardMarkup:
    return ReplyKeyboardBuilder().row(
        KeyboardButton(text="🚫Отмена"),
    ).as_markup(resize_keyboard=True, one_time_keyboard=False)


def accept_markup() -> ReplyKeyboardMarkup:
    return ReplyKeyboardBuilder().row(
        KeyboardButton(text="✅Подтвердить"),
        KeyboardButton(text="🚫Отмена"),
    ).as_markup(resize_keyboard=True, one_time_keyboard=False)


def reject_markup() -> ReplyKeyboardMarkup:
    return ReplyKeyboardBuilder().row(
        KeyboardButton(text="🖼️Без описания"),
        KeyboardButton(text="🚫Отмена"),
    ).as_markup(resize_keyboard=True, one_time_keyboard=False)


@router.message(
    ModerateStates.choosing_category
)
async def on_category_chosen(message: Message, state: FSMContext) -> None:
    callback_data: ModerateCallbackFactory = await state.get_value("callback_data")
    if message.text is None or len(message.text) == 0:
        await message.answer(get_string("services.moderation.empty_category"))
        return
    if message.text == "🚫Отмена":
        await message.reply(
            get_string("services.moderation.category_cancel"),
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        return
    update_service = await services_repository.update_service_fields(
        callback_data.service_id, directory=message.text
    )
    await message.reply(get_string("services.moderation.category_set"), reply_markup=ReplyKeyboardRemove())
    await state.clear()
    await _bot.edit_message_caption(
        chat_id=message.chat.id,
        message_id=callback_data.original_msg,
        caption=create_caption(
            update_service,
            callback_data.author_name
        ),
        reply_markup=create_markup(
            service_id=update_service.id,
            author_name=callback_data.author_name,
            original_msg=callback_data.original_msg
        )
    )


@router.message(
    ModerateStates.refusing
)
async def on_reject_chosen(message: Message, state: FSMContext) -> None:
    callback_data: ModerateCallbackFactory = await state.get_value("callback_data")
    if message.text is None or len(message.text) == 0:
        await message.answer(
            get_string("services.moderation.empty_refuse"),
            reply_markup=reject_markup()
        )
        return
    if message.text == '🚫Отмена':
        await message.reply(
            get_string("services.moderation.refuse_cancel"),
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        return
    update_service = await services_repository.update_service_fields(
        callback_data.service_id, status='refused'
    )
    if message.text == '🖼️Без описания':
        await _bot.send_message(
            update_service.owner,
            get_string("services.moderation.refused_message")
        )
    else:
        await _bot.send_message(
            update_service.owner,
            get_string("services.moderation.refused_message_text", message.text)
        )
    await message.reply(get_string("services.moderation.refuse_confirm"), reply_markup=ReplyKeyboardRemove())
    await state.clear()
    await _bot.edit_message_caption(
        chat_id=message.chat.id,
        message_id=callback_data.original_msg,
        caption=create_caption(
            update_service,
            callback_data.author_name
        )
    )


@router.message(
    ModerateStates.accept
)
async def on_accept_chosen(message: Message, state: FSMContext) -> None:
    callback_data: ModerateCallbackFactory = await state.get_value("callback_data")
    if message.text is None or len(message.text) == 0:
        await message.answer(
            get_string("services.moderation.empty_accept"),
            reply_markup=accept_markup()
        )
        return
    if message.text == '🚫Отмена':
        await message.reply(
            get_string("services.moderation.accept_cancel"),
            reply_markup=ReplyKeyboardRemove()
        )
        return
    elif message.text == '✅Подтвердить':
        update_service = await services_repository.update_service_fields(
            callback_data.service_id, status='published'
        )
        await message.reply(
            get_string("services.moderation.accept_confirm"),
            reply_markup=ReplyKeyboardRemove()
        )
        await _bot.send_message(
            update_service.owner,
            get_string("services.moderation.service_approved")
        )
    else:
        await message.reply(
            get_string("services.moderation.accept_unknown")
        )
        return

    await state.clear()
    await _bot.edit_message_caption(
        chat_id=message.chat.id,
        message_id=callback_data.original_msg,
        caption=create_caption(
            update_service,
            callback_data.author_name
        )
    )
