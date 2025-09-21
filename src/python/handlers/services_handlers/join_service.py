import base64
import io

from aiogram import Router, types
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import ChatJoinRequest, Message, KeyboardButton, FSInputFile, BufferedInputFile, \
    InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from python.logger import logger
from python.storage.repository import users_repository
from python.storage.config import config
from python.storage.strings import get_string
from aiogram.fsm.context import FSMContext
from aiogram import Bot

router = Router()

_bot: Bot


async def init(bot: Bot):
    global _bot
    _bot = bot


class JoinStatuses(StatesGroup):
    waiting_start = State()
    choosing_room = State()
    select_name = State()
    select_surname = State()
    send_picture = State()
    confirm = State()
    waiting_send = State()


@router.chat_join_request()
async def join_request(update: ChatJoinRequest, bot: Bot, state: FSMContext) -> None:
    send = await bot.send_message(
        update.from_user.id,
        get_string(
            "user_service.greeting_start",
            config.refuser.request_life_hours
        ),
        reply_markup=ReplyKeyboardBuilder().row(
            KeyboardButton(text="✅Начать"),
            KeyboardButton(text="❌Отмена")
        ).as_markup(resize_keyboard=True)
    )

    await users_repository.create_or_replace_request(update.from_user.id, send.message_id)

    key = StorageKey(
        bot_id=bot.id,
        chat_id=update.from_user.id,
        user_id=update.from_user.id
    )

    user_state = FSMContext(
        storage=state.storage,
        key=key
    )

    await user_state.set_state(JoinStatuses.waiting_start)


@router.message(
    JoinStatuses.waiting_start
)
async def on_start(message: Message, state: FSMContext) -> None:
    if message.text == "❌Отмена":
        await message.reply(
            get_string("user_service.on_cancel"),
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        await _bot.decline_chat_join_request(
            config.chat_config.chat_id,
            message.from_user.id
        )
    elif message.text == "✅Начать":
        await message.reply(
            get_string("user_service.select_room"),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text="❌Отмена")
            ).as_markup(resize_keyboard=True, one_time_keyboard=True)
        )
        await state.set_state(JoinStatuses.choosing_room)
    else:
        await message.reply(
            get_string("user_service.greeting_unknown"),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text="✅Начать"),
                KeyboardButton(text="❌Отмена")
            ).as_markup(resize_keyboard=True, one_time_keyboard=True)
        )


@router.message(
    JoinStatuses.choosing_room
)
async def on_room_chosen(message: Message, state: FSMContext) -> None:
    if message.text == "❌Отмена":
        await message.reply(
            get_string("user_service.on_cancel"),
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        await _bot.decline_chat_join_request(
            config.chat_config.chat_id,
            message.from_user.id
        )
    elif not message.text or len(message.text) != 3 or not message.text.isdigit() or int(message.text) < 0:
        await message.reply(
            get_string("user_service.select_room_unknown"),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text="❌Отмена")
            ).as_markup(resize_keyboard=True, one_time_keyboard=True)
        )
    else:
        await state.update_data(room=int(message.text))
        await message.reply(
            get_string("user_service.select_name"),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text="❌Отмена")
            ).as_markup(resize_keyboard=True, one_time_keyboard=True)
        )
        await state.set_state(JoinStatuses.select_name)


@router.message(
    JoinStatuses.select_name
)
async def on_name_chosen(message: Message, state: FSMContext) -> None:
    if message.text == "❌Отмена":
        await message.reply(
            get_string("user_service.on_cancel"),
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        await _bot.decline_chat_join_request(
            config.chat_config.chat_id,
            message.from_user.id
        )
    else:
        await state.update_data(name=message.text)
        await message.reply(
            get_string("user_service.select_surname"),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text="❌Отмена")
            ).as_markup(resize_keyboard=True, one_time_keyboard=True)
        )
        await state.set_state(JoinStatuses.select_surname)


cached_confirm_sample_file_id = None


@router.message(
    JoinStatuses.select_surname
)
async def on_surname_chosen(message: Message, state: FSMContext) -> None:
    if message.text == "❌Отмена":
        await message.reply(
            get_string("user_service.on_cancel"),
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        await _bot.decline_chat_join_request(
            config.chat_config.chat_id,
            message.from_user.id
        )
    else:
        await state.update_data(surname=message.text)

        global cached_confirm_sample_file_id

        while True:
            if cached_confirm_sample_file_id is None:
                image_path = "./src/res/images/join_confirm_sample.jpg"
                sent: Message = await message.reply_photo(
                    photo=FSInputFile(image_path),
                    caption=get_string("user_service.confirm_picture"),
                    show_caption_above_media=True,
                    reply_markup=ReplyKeyboardBuilder().row(
                        KeyboardButton(text="❌Отмена")
                    ).as_markup(resize_keyboard=True, one_time_keyboard=True)
                )
                if sent.photo:
                    cached_confirm_sample_file_id = sent.photo[-1].file_id
            else:
                try:
                    await message.reply_photo(
                        photo=cached_confirm_sample_file_id,
                        caption=get_string("user_service.confirm_picture"),
                        show_caption_above_media=True,
                        reply_markup=ReplyKeyboardBuilder().row(
                            KeyboardButton(text="❌Отмена")
                        ).as_markup(resize_keyboard=True, one_time_keyboard=True)
                    )
                except Exception as e:
                    logger.error(f"{e}")
                    cached_confirm_sample_file_id = None
                    continue
            break

        await state.set_state(JoinStatuses.send_picture)


@router.message(
    JoinStatuses.send_picture
)
async def on_picture_chosen(message: Message, state: FSMContext) -> None:
    if message.text == "❌Отмена":
        await message.reply(
            get_string("user_service.on_cancel"),
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        await _bot.decline_chat_join_request(
            config.chat_config.chat_id,
            message.from_user.id
        )
        return
    if not message.photo:
        await message.reply(
            get_string("user_service.not_photo_and_empty"),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text="❌Отмена")
            ).as_markup(resize_keyboard=True, one_time_keyboard=True)
        )
        return

    largest_photo = message.photo[-1]
    photo_buffer = io.BytesIO()
    await _bot.download(
        file=largest_photo.file_id,
        destination=photo_buffer
    )
    photo_buffer.seek(0)
    photo_bytes = photo_buffer.read()
    photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')

    await state.update_data(
        image=photo_base64
    )

    await message.reply_photo(
        photo=largest_photo.file_id,
        caption=get_string(
            "user_service.confirm",
            await state.get_value("name"),
            await state.get_value("surname"),
            await state.get_value("room")
        ),
        reply_markup=ReplyKeyboardBuilder().row(
            KeyboardButton(text="✅Отправить"),
            KeyboardButton(text="❌Отмена")
        ).as_markup(resize_keyboard=True, one_time_keyboard=True)
    )
    await state.set_state(JoinStatuses.waiting_send)


class ModerateUserCallbackFactory(CallbackData, prefix="moderateuser"):
    action: str
    database_id: int
    message: int


@router.message(
    JoinStatuses.waiting_send
)
async def on_send_chosen(message: Message, state: FSMContext) -> None:
    if message.text == "❌Отмена":
        await message.reply(
            get_string("user_service.on_cancel"),
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        await _bot.decline_chat_join_request(
            config.chat_config.chat_id,
            message.from_user.id
        )
    elif message.text == "✅Отправить":
        await users_repository.delete_users_by_user_id(message.from_user.id)
        await users_repository.mark_request_processed(message.from_user.id)
        image = await state.get_value("image")
        insert_id = await users_repository.add_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            fullname=message.from_user.full_name,
            name=await state.get_value("name"),
            surname=await state.get_value("surname"),
            room=await state.get_value("room"),
            image=image
        )
        image_bytes = base64.b64decode(image)
        image_stream = io.BytesIO(image_bytes)
        media = BufferedInputFile(image_stream.read(), filename=f"preview.jpg")
        send = await _bot.send_photo(
            chat_id=config.chat_config.admin_chat_id,
            photo=media,
            caption=new_request_message(
                message.from_user.full_name,
                message.from_user.username,
                message.from_user.id,
                get_string("user_service.moderation.request_status_on_moderation"),
                await state.get_value("name"),
                await state.get_value("surname"),
                await state.get_value("room")
            ),
            reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(
                text='🚫Отклонить',
                callback_data='.'
            )).row(InlineKeyboardButton(
                text='✅Одобрить',
                callback_data='.'
            )).as_markup()
        )
        await send.edit_reply_markup(reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(
            text='🚫Отклонить',
            callback_data=ModerateUserCallbackFactory(
                action="refuse",
                database_id=insert_id,
                message=send.message_id
            ).pack()
        )).row(InlineKeyboardButton(
            text='✅Одобрить',
            callback_data=ModerateUserCallbackFactory(
                action="accept",
                database_id=insert_id,
                message=send.message_id
            ).pack()
        )).as_markup())
        await message.reply(get_string("user_service.confirm_sent"), reply_markup=ReplyKeyboardRemove())
        await state.clear()
    else:
        await message.reply(
            get_string("user_service.confirm_unknown"),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text="✅Отправить"),
                KeyboardButton(text="❌Отмена")
            ).as_markup(resize_keyboard=True, one_time_keyboard=True)
        )


class JoinModerateStatuses(StatesGroup):
    waiting_accept = State()
    waiting_refuse = State()
    waiting_refuse_description = State()


@router.callback_query(ModerateUserCallbackFactory.filter())
async def callbacks_moderate_buttons(
        callback: types.CallbackQuery,
        callback_data: ModerateUserCallbackFactory,
        state: FSMContext,
) -> None:
    if not callback.message:
        return
    match callback_data.action:
        case "accept":
            await callback.message.reply(
                get_string("user_service.moderation.accept_confirm"),
                reply_markup=ReplyKeyboardBuilder().row(
                    KeyboardButton(text="✅Подтвердить"),
                    KeyboardButton(text="🚫Отмена")
                ).as_markup(resize_keyboard=True, one_time_keyboard=False)
            )
            await state.update_data(callback_data=callback_data.pack())
            await state.set_state(JoinModerateStatuses.waiting_accept)
        case "refuse":
            await callback.message.reply(
                get_string("user_service.moderation.refuse_confirm"),
                reply_markup=ReplyKeyboardBuilder().row(
                    KeyboardButton(text="Отклонить"),
                    KeyboardButton(text="🚫Отмена")
                ).as_markup(resize_keyboard=True, one_time_keyboard=False)
            )
            await state.update_data(callback_data=callback_data.pack())
            await state.set_state(JoinModerateStatuses.waiting_refuse)
    await callback.answer()


@router.message(
    JoinModerateStatuses.waiting_accept
)
async def on_join_accept(message: Message, state: FSMContext) -> None:
    if message.text == "🚫Отмена":
        await message.reply(
            get_string("user_service.moderation.accept_confirm_cancel"),
            reply_markup=ReplyKeyboardRemove()
        )
    elif message.text == "✅Подтвердить":
        callback_data: ModerateUserCallbackFactory = ModerateUserCallbackFactory.unpack(
            await state.get_value("callback_data")
        )
        await message.reply(
            get_string("user_service.moderation.accept_confirmed"),
            reply_markup=ReplyKeyboardRemove()
        )
        database_user = await users_repository.get_user_by_id(callback_data.database_id)
        await _bot.approve_chat_join_request(
            config.chat_config.chat_id,
            database_user.user_id
        )
        await _bot.edit_message_caption(
            chat_id=config.chat_config.admin_chat_id,
            message_id=callback_data.message,
            caption=new_request_message(
                database_user.fullname,
                database_user.username,
                database_user.user_id,
                get_string("user_service.moderation.request_status_approved"),
                database_user.name,
                database_user.surname,
                database_user.room
            ),
            reply_markup=None
        )
        await _bot.send_message(
            database_user.user_id,
            get_string("user_service.moderation.accepted")
        )
        await users_repository.update_user_fields(
            callback_data.database_id,
            status="accept",
            processed_by=message.from_user.id,
            processed_by_fullname=message.from_user.full_name,
            processed_by_username=message.from_user.username
        )
    else:
        await message.reply(get_string("user_service.moderation.accept_confirm_unknown"))


@router.message(
    JoinModerateStatuses.waiting_refuse
)
async def on_refuse_accept(message: Message, state: FSMContext) -> None:
    if message.text == "🚫Отмена":
        await message.reply(
            get_string("user_service.moderation.refuse_confirm_cancel"),
            reply_markup=ReplyKeyboardRemove()
        )
    elif message.text == "Отклонить":
        await message.reply(
            get_string("user_service.moderation.refuse_commenting"),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text="Без причины"),
                KeyboardButton(text="🚫Отмена")
            ).as_markup(resize_keyboard=True, one_time_keyboard=False)
        )
        await state.set_state(JoinModerateStatuses.waiting_refuse_description)
    else:
        await message.reply(get_string("user_service.moderation.refuse_confirm_unknown"))


@router.message(
    JoinModerateStatuses.waiting_refuse_description
)
async def on_refuse_description_accept(message: Message, state: FSMContext) -> None:
    if message.text == "🚫Отмена":
        await message.reply(
            get_string("user_service.moderation.refuse_confirm_cancel"),
            reply_markup=ReplyKeyboardRemove()
        )

    if message.text == "Без причины":
        reason = None
    else:
        reason = message.text

    callback_data: ModerateUserCallbackFactory = ModerateUserCallbackFactory.unpack(
        await state.get_value("callback_data")
    )
    database_user = await users_repository.get_user_by_id(callback_data.database_id)
    await _bot.decline_chat_join_request(
        config.chat_config.chat_id,
        database_user.user_id
    )
    await _bot.edit_message_caption(
        chat_id=config.chat_config.admin_chat_id,
        message_id=callback_data.message,
        caption=new_request_message(
            database_user.fullname,
            database_user.username,
            database_user.user_id,
            get_string("user_service.moderation.request_status_refused"),
            database_user.name,
            database_user.surname,
            database_user.room
        ),
        reply_markup=None
    )
    await users_repository.update_user_fields(
        callback_data.database_id,
        status="refuse",
        processed_by=message.from_user.id,
        processed_by_fullname=message.from_user.full_name,
        processed_by_username=message.from_user.username,
        refuse_reason=reason
    )
    if reason:
        await _bot.send_message(
            database_user.user_id,
            get_string("user_service.moderation.refused_reason", reason)
        )
        await message.reply(
            get_string("user_service.moderation.refuse_confirmed_commented", reason),
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await _bot.send_message(
            database_user.user_id,
            get_string("user_service.moderation.refused", reason)
        )
        await message.reply(
            get_string("user_service.moderation.refuse_confirmed"),
            reply_markup=ReplyKeyboardRemove()
        )


def new_request_message(
        fullname: str, username: str, user_id: int, status: str, first_name: str, last_name: str, room: int
) -> str:
    return get_string(
        "user_service.moderation.new_request",
        fullname,
        username,
        user_id,
        status,
        first_name,
        last_name,
        room
    )
