import base64
import io
from enum import Enum

from aiogram import Router, types
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import ChatJoinRequest, Message, KeyboardButton, FSInputFile, BufferedInputFile, \
    InlineKeyboardButton, ReplyKeyboardRemove, User
from aiogram.utils.deep_linking import create_start_link
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
    choosing_room = State()
    select_name = State()
    select_surname = State()
    send_picture = State()
    confirm = State()
    waiting_send = State()


class JoinGreetingActions(Enum):
    cancel = 'cancel'


class JoinGreetingCallbackFactory(CallbackData, prefix="greeting_button"):
    action: JoinGreetingActions


@router.chat_join_request()
async def join_request(update: ChatJoinRequest, bot: Bot, state: FSMContext) -> None:
    send = await bot.send_message(
        update.from_user.id,
        get_string(
            "user_service.greeting_start",
            config.refuser.request_life_hours
        ),
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(
                text=get_string("user_service.greeting_button_start"),
                url=await create_start_link(
                    _bot,
                    get_string("user_service.greeting_button_start_payload"),
                    encode=True
                )
            )
        ).row(
            InlineKeyboardButton(
                text=get_string("user_service.greeting_button_cancel"),
                callback_data=JoinGreetingCallbackFactory(
                    action=JoinGreetingActions.cancel
                ).pack()
            )
        ).as_markup()
    )

    key = StorageKey(
        bot_id=bot.id,
        chat_id=update.from_user.id,
        user_id=update.from_user.id
    )

    user_state = FSMContext(
        storage=state.storage,
        key=key
    )

    await user_state.update_data(greeting_message=send.message_id)

    await users_repository.create_or_replace_request(update.from_user.id, send.message_id)


@router.callback_query(JoinGreetingCallbackFactory.filter())
async def on_greeting_callback(
        callback: types.CallbackQuery,
        callback_data: JoinGreetingCallbackFactory,
        state: FSMContext
):
    if not callback.message:
        return

    await callback.message.delete_reply_markup()
    await state.clear()

    match callback_data.action:
        case JoinGreetingActions.cancel:
            await users_repository.mark_request_processed(callback.from_user.id)
            await callback.message.reply(
                get_string("user_service.on_cancel"),
                reply_markup=ReplyKeyboardRemove()
            )
            await _bot.decline_chat_join_request(
                config.chat_config.chat_id,
                callback.from_user.id
            )


async def on_accept_join_process(message: Message, state: FSMContext):
    greeting_message_id: int = await state.get_value('greeting_message')
    await _bot.edit_message_reply_markup(
        chat_id=message.chat.id, message_id=greeting_message_id, reply_markup=None
    )
    await state.clear()
    await message.reply(
        get_string("user_service.select_room"),
        reply_markup=ReplyKeyboardBuilder().row(
            KeyboardButton(text="❌Отмена")
        ).as_markup(resize_keyboard=True, one_time_keyboard=True)
    )
    await state.set_state(JoinStatuses.choosing_room)


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
        await users_repository.mark_request_processed(message.from_user.id)
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
        await users_repository.mark_request_processed(message.from_user.id)
    elif not message.text or len(message.text) == 0:
        await message.reply(
            get_string("user_service.name_empty"),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text="❌Отмена")
            ).as_markup(resize_keyboard=True, one_time_keyboard=True)
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
        await users_repository.mark_request_processed(message.from_user.id)
    elif not message.text or len(message.text) == 0:
        await message.reply(
            get_string("user_service.surname_empty"),
            reply_markup=ReplyKeyboardBuilder().row(
                KeyboardButton(text="❌Отмена")
            ).as_markup(resize_keyboard=True, one_time_keyboard=True)
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
        await users_repository.mark_request_processed(message.from_user.id)
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
        await users_repository.mark_request_processed(message.from_user.id)
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
                get_string("user_service.moderation.request_status.on_moderation"),
                await state.get_value("name"),
                await state.get_value("surname"),
                await state.get_value("room"),
                get_string('user_service.moderation.actions.choose')
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
    waiting_refuse_description = State()


class ModerateButtonsAction(Enum):
    ACCEPT_CONFIRM = 'accept_confirm'
    REFUSE_CONFIRM = 'refuse_confirm'
    REFUSE_NO_DESCRIPTION = 'refuse_description'
    CANCEL = 'cancel'


class ModerateButtonsFactory(CallbackData, prefix="moderatebuttons"):
    action: ModerateButtonsAction
    database_id: int
    message: int


@router.callback_query(ModerateUserCallbackFactory.filter())
async def callbacks_moderate_buttons(
        callback: types.CallbackQuery,
        callback_data: ModerateUserCallbackFactory
) -> None:
    if not callback.message:
        return
    database_user = await users_repository.get_user_by_id(callback_data.database_id)
    match callback_data.action:
        case "accept":
            await callback.message.edit_caption(
                caption=new_request_message(
                    database_user.fullname,
                    database_user.username,
                    database_user.user_id,
                    get_string("user_service.moderation.request_status.on_moderation"),
                    database_user.name,
                    database_user.surname,
                    database_user.room,
                    get_string('user_service.moderation.actions.accept_confirm')
                ),
                reply_markup=InlineKeyboardBuilder().row(
                    InlineKeyboardButton(
                        text="✅Подтвердить",
                        callback_data=ModerateButtonsFactory(
                            action=ModerateButtonsAction.ACCEPT_CONFIRM,
                            database_id=callback_data.database_id,
                            message=callback_data.message
                        ).pack()
                    )
                ).row(
                    InlineKeyboardButton(
                        text="🚫Отмена",
                        callback_data=ModerateButtonsFactory(
                            action=ModerateButtonsAction.CANCEL,
                            database_id=callback_data.database_id,
                            message=callback_data.message
                        ).pack()
                    )
                ).as_markup()
            )
        case "refuse":
            await callback.message.edit_caption(
                caption=new_request_message(
                    database_user.fullname,
                    database_user.username,
                    database_user.user_id,
                    get_string("user_service.moderation.request_status.on_moderation"),
                    database_user.name,
                    database_user.surname,
                    database_user.room,
                    get_string('user_service.moderation.actions.refuse_confirm')
                ),
                reply_markup=InlineKeyboardBuilder().row(
                    InlineKeyboardButton(
                        text="❌Отклонить",
                        callback_data=ModerateButtonsFactory(
                            action=ModerateButtonsAction.REFUSE_CONFIRM,
                            database_id=callback_data.database_id,
                            message=callback_data.message
                        ).pack()
                    )
                ).row(
                    InlineKeyboardButton(
                        text="🚫Отмена",
                        callback_data=ModerateButtonsFactory(
                            action=ModerateButtonsAction.CANCEL,
                            database_id=callback_data.database_id,
                            message=callback_data.message
                        ).pack()
                    )
                ).as_markup()
            )

    await callback.answer()


@router.callback_query(ModerateButtonsFactory.filter())
async def on_join_accept(
        callback: types.CallbackQuery,
        callback_data: ModerateButtonsFactory,
        state: FSMContext
) -> None:
    if not callback.message:
        return
    database_user = await users_repository.get_user_by_id(callback_data.database_id)
    match callback_data.action:
        case ModerateButtonsAction.CANCEL:
            await callback.message.edit_caption(
                caption=new_request_message(
                    database_user.fullname,
                    database_user.username,
                    database_user.user_id,
                    get_string("user_service.moderation.request_status.on_moderation"),
                    database_user.name,
                    database_user.surname,
                    database_user.room,
                    get_string('user_service.moderation.actions.choose')
                ),
                reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(
                    text='🚫Отклонить',
                    callback_data=ModerateUserCallbackFactory(
                        action="refuse",
                        database_id=callback_data.database_id,
                        message=callback_data.message
                    ).pack()
                )).row(InlineKeyboardButton(
                    text='✅Одобрить',
                    callback_data=ModerateUserCallbackFactory(
                        action="accept",
                        database_id=callback_data.database_id,
                        message=callback_data.message
                    ).pack()
                )).as_markup()
            )
            await state.clear()
        case ModerateButtonsAction.ACCEPT_CONFIRM:
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
                    get_string(
                        "user_service.moderation.request_status.approved.username",
                        callback.from_user.username
                    ) if callback.from_user.username else get_string(
                        "user_service.moderation.request_status.approved.nousername",
                        callback.from_user.id, callback.from_user.full_name
                    ),
                    database_user.name,
                    database_user.surname,
                    database_user.room
                ),
                reply_markup=None
            )
            await _bot.send_message(
                database_user.user_id,
                get_string("user_service.moderation.user_answer.accepted")
            )
            await users_repository.update_user_fields(
                callback_data.database_id,
                status="accept",
                processed_by=callback.from_user.id,
                processed_by_fullname=callback.from_user.full_name,
                processed_by_username=callback.from_user.username
            )
            await state.clear()
        case ModerateButtonsAction.REFUSE_CONFIRM:
            await callback.message.edit_caption(
                caption=new_request_message(
                    database_user.fullname,
                    database_user.username,
                    database_user.user_id,
                    get_string("user_service.moderation.request_status.on_moderation"),
                    database_user.name,
                    database_user.surname,
                    database_user.room,
                    get_string('user_service.moderation.actions.refuse_choose_description')
                ),
                reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(
                    text='🖼️Без причины',
                    callback_data=ModerateButtonsFactory(
                        action=ModerateButtonsAction.REFUSE_NO_DESCRIPTION,
                        database_id=callback_data.database_id,
                        message=callback_data.message
                    ).pack()
                )).row(InlineKeyboardButton(
                    text='🚫Отмена',
                    callback_data=ModerateButtonsFactory(
                        action=ModerateButtonsAction.CANCEL,
                        database_id=callback_data.database_id,
                        message=callback_data.message
                    ).pack()
                )).as_markup()
            )

            await state.update_data(callback_data=callback_data.pack())
            await state.set_state(JoinModerateStatuses.waiting_refuse_description)
        case ModerateButtonsAction.REFUSE_NO_DESCRIPTION:
            await refuse_user(None, state, callback.from_user)
            await state.clear()
    await callback.answer()


async def refuse_user(reason: str | None, state: FSMContext, from_user: User) -> None:
    callback_data: ModerateButtonsFactory = ModerateButtonsFactory.unpack(
        await state.get_value("callback_data")
    )
    database_user = await users_repository.get_user_by_id(callback_data.database_id)
    await _bot.decline_chat_join_request(
        config.chat_config.chat_id,
        database_user.user_id
    )
    if from_user.username:
        if reason:
            status = get_string(
                "user_service.moderation.request_status.refused.username.commented",
                from_user.username, reason
            )
        else:
            status = get_string(
                "user_service.moderation.request_status.refused.username.nocomment",
                from_user.username
            )
    else:
        if reason:
            status = get_string(
                "user_service.moderation.request_status.refused.nousername.commented",
                from_user.id, from_user.full_name, reason
            )
        else:
            status = get_string(
                "user_service.moderation.request_status.refused.nousername.nocomment",
                from_user.id, from_user.full_name
            )

    await _bot.edit_message_caption(
        chat_id=config.chat_config.admin_chat_id,
        message_id=callback_data.message,
        caption=new_request_message(
            database_user.fullname,
            database_user.username,
            database_user.user_id,
            status,
            database_user.name,
            database_user.surname,
            database_user.room
        ),
        reply_markup=None
    )
    await users_repository.update_user_fields(
        callback_data.database_id,
        status="refuse",
        processed_by=from_user.id,
        processed_by_fullname=from_user.full_name,
        processed_by_username=from_user.username,
        refuse_reason=reason
    )
    await _bot.send_message(
        database_user.user_id,
        get_string(
            "user_service.moderation.user_answer.refused.commented", reason
        ) if reason else get_string(
            "user_service.moderation.user_answer.refused.nocomment"
        )
    )


@router.message(
    JoinModerateStatuses.waiting_refuse_description
)
async def on_refuse_description_accept(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text) == 0:
        await message.reply(get_string(
            'user_service.moderation.refuse_confirm_empty'
        ))
    else:
        await refuse_user(message.text, state, message.from_user)
        await state.clear()


def new_request_message(
        fullname: str, username: str | None, user_id: int, status: str,
        first_name: str, last_name: str, room: int, action: str = ''
) -> str:
    if username:
        return get_string(
            "user_service.moderation.new_request",
            fullname,
            username,
            user_id,
            status,
            first_name,
            last_name,
            room,
            action
        )
    else:
        return get_string(
            "user_service.moderation.new_request_nousername",
            user_id,
            fullname,
            user_id,
            status,
            first_name,
            last_name,
            room,
            action
        )
