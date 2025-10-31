import asyncio
import base64
import io
import urllib.parse
from enum import Enum

from aiogram import Bot, Router
from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InaccessibleMessage, InlineKeyboardButton, InputMediaPhoto, Message, \
    FSInputFile, BufferedInputFile
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.keyboard import InlineKeyboardBuilder

from python.handlers.echo_commands import create_delete_task
from python.handlers.services_handlers import add_service_commands, my_services_command
from python.storage.repository import services_repository
from python.storage.strings import get_string
from python.utils import check_blacklisted, log_exception
from aiogram.filters.callback_data import CallbackData

# === ЗАМЕНА ИМПОРТОВ ===
from python.storage import config as config_module
from python import logger as logger_module

_bot_username: str
_bot: Bot


async def init(bot_username: str, bot: Bot):
    global _bot_username, _bot
    _bot_username = bot_username
    _bot = bot


router = Router()


class ServicesActions(Enum):
    ADD_SERVICE = "add_service"
    MY_SERVICES = "my_services"


class ServicesHandlerFactory(CallbackData, prefix="servicesbuttons"):
    action: ServicesActions


class ServicesCallbackFactory(CallbackData, prefix="services"):
    path: str
    is_service: bool = False
    offset: int = 0


PAGE_SIZE = 5


async def parse_folder_keyboard(lang: str, path: str, offset=0, is_pm=False) -> tuple[InlineKeyboardBuilder, int, int]:
    services = await services_repository.get_service_list(path)
    builder = InlineKeyboardBuilder()
    logger_module.logger.debug(f"{path}: {services}")

    if path == "/":
        if is_pm:
            builder.row(
                InlineKeyboardButton(
                    text=get_string(lang, "services.add_button"),
                    callback_data=ServicesHandlerFactory(action=ServicesActions.ADD_SERVICE).pack()
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text=get_string(lang, "services.add_button"),
                    url=await create_start_link(_bot, 'addservice', encode=True)
                )
            )
    if is_pm:
        builder.row(
            InlineKeyboardButton(
                text=get_string(lang, "services.my_services"),
                callback_data=ServicesHandlerFactory(action=ServicesActions.MY_SERVICES).pack()
            )
        )

    if len(services) > PAGE_SIZE:
        cropped_services = services[offset:offset + PAGE_SIZE]
    else:
        cropped_services = services

    for service in cropped_services:
        if service.is_folder:
            button_path = service.folder_dest
            text = get_string(lang, "services.folder_button", service.name)
        else:
            button_path = service.service_id
            text = get_string(
                lang,
                "services.service_button",
                service.name, service.cost, service.cost_per,
                service.owner
            )

        if button_path is not None:
            builder.row(
                InlineKeyboardButton(
                    text=text,
                    callback_data=ServicesCallbackFactory(
                        path=str(button_path),
                        is_service=not service.is_folder
                    ).pack()
                )
            )

    if len(services) > PAGE_SIZE:
        row = []
        if offset > 0:
            row.append(
                InlineKeyboardButton(
                    text=get_string(lang, "services.prev_button"),
                    callback_data=ServicesCallbackFactory(
                        path=path,
                        offset=offset - PAGE_SIZE
                    ).pack()
                )
            )
        if offset + PAGE_SIZE < len(services):
            row.append(
                InlineKeyboardButton(
                    text=get_string(lang, "services.next_button"),
                    callback_data=ServicesCallbackFactory(
                        path=path,
                        offset=offset + PAGE_SIZE
                    ).pack()
                )
            )
        builder.row(*row)

    if path != "/":
        path_split = path.strip("/").split("/")

        del path_split[-1]
        parent_path = "/" + "/".join(path_split)
        builder.row(InlineKeyboardButton(
            text=get_string(lang, "services.back_button"),
            callback_data=ServicesCallbackFactory(
                path=parent_path
            ).pack()
        ))

    return builder, offset // PAGE_SIZE + 1, len(services) // PAGE_SIZE + 1


@router.callback_query(ServicesHandlerFactory.filter())
async def add_service_button(
        callback: types.CallbackQuery,
        callback_data: ServicesHandlerFactory,
        state: FSMContext
):
    try:
        if not callback.message:
            return
        if callback_data.action == ServicesActions.ADD_SERVICE:
            await callback.answer()
            await add_service_commands.on_addservice(callback.message, state, callback.from_user.language_code)
        elif callback_data.action == ServicesActions.MY_SERVICES:
            await my_services_command.on_my_services(callback.message, state, callback.from_user.language_code)
            await callback.answer(text="SOON")
    except Exception as e:
        await log_exception(e, callback, state=state)


@router.message(Command("services"))
@router.message(lambda message: message.text and message.text.lower() in ["услуги"])
async def command_services_handler(message: Message) -> None:
    try:
        if await check_blacklisted(message):
            return
        builder, page, pages = await parse_folder_keyboard(message.from_user.language_code, "/",
                                                           is_pm=message.chat.type == 'private')

        caption_lines = [get_string(message.from_user.language_code, "services.folder_caption.header").strip()]
        if pages > 1:
            caption_lines.append(
                get_string(
                    message.from_user.language_code,
                    'services.folder_caption.page',
                    page, pages
                ).strip()
            )

        await message.reply_photo(
            photo=FSInputFile('./src/res/images/services/header.jpg'),
            caption='\n'.join(caption_lines),
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        asyncio.create_task(create_delete_task(
            message, await message.reply(
                get_string(
                    message.from_user.language_code,
                    "exceptions.uncause",
                    logger_module.logger.error(e, message),
                    config_module.config.chat_config.owner_username
                )
            )
        ))


@router.callback_query(ServicesCallbackFactory.filter())
async def callbacks_num_change_fab(
        callback: types.CallbackQuery,
        callback_data: ServicesCallbackFactory
) -> None:
    try:
        if not callback.message:
            return
        if callback_data.is_service:
            service = await services_repository.find_service(int(callback_data.path))
            if service is None:
                return
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(
                text=get_string(
                    callback.from_user.language_code, "services.go_button.title"
                ),
                url=get_string(
                    callback.from_user.language_code,
                    "services.go_button.url_placeholder",
                    service.owner,
                    urllib.parse.quote(service.name)
                )
            ))
            builder.row(InlineKeyboardButton(
                text=get_string(callback.from_user.language_code, "services.back_button"),
                callback_data=ServicesCallbackFactory(
                    path=service.directory
                ).pack()
            ))

            if not callback.message or isinstance(callback.message, InaccessibleMessage):
                await callback.answer(
                    show_alert=True,
                    text="Server error"
                )
                logger_module.logger.error(f"Callback message not present or it is InaccessibleMessage: {callback.message}")
                return
            try:
                if service.image:
                    image_bytes = base64.b64decode(service.image)
                    image_stream = io.BytesIO(image_bytes)
                    media = BufferedInputFile(image_stream.read(), filename=f"{service.id}.jpg")
                else:
                    media = FSInputFile('./src/res/images/services/no_image.jpg')
                await callback.message.edit_media(
                    InputMediaPhoto(
                        media=media,
                        caption=get_string(
                            callback.from_user.language_code,
                            "services.author_page_description", service.name, int(service.cost), service.cost_per,
                            service.description
                        ) if service.description else get_string(
                            "services.author_page", service.name, int(service.cost), service.cost_per
                        ),
                    ),
                    reply_markup=builder.as_markup()
                )
            except Exception as e:
                logger_module.logger.error(f"Cannot proccess image: {e}")
                await callback.message.edit_caption(
                    caption=get_string(
                        callback.from_user.language_code,
                        "services.author_page_description", service.name, int(service.cost), service.cost_per,
                        service.description
                    ) if service.description else get_string(
                        callback.from_user.language_code,
                        "services.author_page", service.name, int(service.cost), service.cost_per
                    ),
                    reply_markup=builder.as_markup()
                )
        else:
            if not callback.message or isinstance(callback.message, InaccessibleMessage):
                await callback.answer(
                    show_alert=True,
                    text="Server error"
                )
                logger_module.logger.error(f"Callback message not present or it is InaccessibleMessage: {callback.message}")
                return
            new_keyboard, page, pages = await parse_folder_keyboard(
                callback.from_user.language_code,
                callback_data.path,
                callback_data.offset,
                callback.message.chat.type == 'private'
            )

            caption_lines = [get_string(callback.from_user.language_code, "services.folder_caption.header").strip()]
            strip_path = callback_data.path.strip("/")
            if strip_path:
                caption_lines.append(
                    get_string(callback.from_user.language_code, 'services.folder_caption.folder.sep').join(
                        get_string(
                            callback.from_user.language_code, 'services.folder_caption.folder.title', part
                        ) for part in strip_path.split("/")
                    ).strip()
                )
            if pages > 1:
                caption_lines.append(
                    get_string(
                        callback.from_user.language_code,
                        'services.folder_caption.page',
                        page, pages
                    ).strip()
                )

            try:
                await callback.message.edit_media(
                    InputMediaPhoto(
                        media=FSInputFile('./src/res/images/services/header.jpg'),
                        caption='\n'.join(caption_lines)
                    ),
                    reply_markup=new_keyboard.as_markup()
                )
            except Exception:
                await callback.message.edit_caption(
                    photo=FSInputFile('./src/res/images/services/header.jpg'),
                    caption='\n'.join(caption_lines),
                    reply_markup=new_keyboard.as_markup()
                )

        await callback.answer()
    except Exception as e:
        await log_exception(e, callback)