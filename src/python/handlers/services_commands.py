from aiogram import Router
from aiogram import types
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InaccessibleMessage, InlineKeyboardButton, InputMediaPhoto, Message, FSInputFile, BufferedInputFile
from attr import dataclass
from aiogram.utils.keyboard import InlineKeyboardBuilder

from python.logger import logger
from python.storage import services_repository
import base64
import io

from ..storage.strings import get_string


_bot_username: str


async def init(bot_username: str):
    global _bot_username
    _bot_username = bot_username
    await services_repository.init_database_module()



router = Router()


class ServicesCallbackFactory(CallbackData, prefix="services"):
    path: str
    is_service: bool = False
    offset: int = 0


PAGE_SIZE = 2


async def parse_folder_keyboard(path: str, offset=0) -> InlineKeyboardBuilder:
    services = await services_repository.get_service_list(path)
    builder = InlineKeyboardBuilder()
    print(f"{path}:", services)

    builder.row(
        InlineKeyboardButton(
            text="Добавить услугу",
            url=f"https://t.me/{_bot_username}?text=/addservice"
        )
    )

    if len(services) > PAGE_SIZE:
        l = services[offset:offset+PAGE_SIZE]
    else:
        l = services

    for service in l:
        button_path: str | int | None = service.folder_dest if service.is_folder else service.service_id
        if button_path is not None:
            builder.row(
                InlineKeyboardButton(
                    text = f"📂 {service.name}" if service.is_folder else f"{service.name} ➡️",
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
                    text="⏪ Previous page",
                    callback_data=ServicesCallbackFactory(
                        path=path,
                        offset=offset - PAGE_SIZE
                    ).pack()
                )
            )
        if offset + PAGE_SIZE < len(services):
            row.append(
                InlineKeyboardButton(
                    text="Next page ⏩",
                    callback_data=ServicesCallbackFactory(
                        path=path,
                        offset=offset + PAGE_SIZE
                    ).pack()
                )
            )
        print(len(services), PAGE_SIZE, offset)
        print(row)
        builder.row(*row)


    if path != "/":
        path_split = path.strip("/").split("/")

        del path_split[-1]
        parent_path = "/" + "/".join(path_split)
        builder.row(InlineKeyboardButton(
            text="Назад ⤴️",
            callback_data=ServicesCallbackFactory(
                path=parent_path
            ).pack()
        ))

    return builder


@router.message(Command("services"))
@router.message(lambda message: message.text and message.text.lower() in ["услуги"])
async def command_services_handler(message: Message) -> None:
    builder = await parse_folder_keyboard("/")

    await message.reply_photo(
        photo=FSInputFile('./src/res/images/empty_service.jpg'),
        caption='Список доступных услуг',
        reply_markup=builder.as_markup()
    )


@router.callback_query(ServicesCallbackFactory.filter())
async def callbacks_num_change_fab(
    callback: types.CallbackQuery, 
    callback_data: ServicesCallbackFactory
) -> None:
    print("\n", callback_data)
    if not callback.message:
        return
    if callback_data.is_service:
        service = await services_repository.find_service(int(callback_data.path))
        if service is None:
            return
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text="Написать",
            url=f"https://t.me/{service.username}?text=Привет%20я%20по%20поводу%20услуги"
        ))
        builder.row(InlineKeyboardButton(
            text="Назад ⤴️",
            callback_data=ServicesCallbackFactory(
                path=service.directory
            ).pack()
        ))

        if not callback.message or isinstance(callback.message, InaccessibleMessage):
            await callback.answer(
                show_alert=True,
                text="Server error"
            )
            logger.error(f"Callback message not present or it is InaccessibleMessage: {callback.message}")
            return 
        try:
            if service.image: 
                image_bytes = base64.b64decode(service.image)
                image_stream = io.BytesIO(image_bytes)
                media = BufferedInputFile(image_stream.read(), filename=f"{service.id}.jpg")
            else:
                media = FSInputFile('./src/res/images/empty_service.jpg')
            await callback.message.edit_media(
                InputMediaPhoto(
                    media=media,
                    caption=get_string(
                        "services.author_page_description", service.name, int(service.cost), service.cost_per, service.description
                    ) if service.description else get_string(
                        "services.author_page", service.name, int(service.cost), service.cost_per
                    ),
                ),
                reply_markup=builder.as_markup()
            )
        except Exception as e:
            logger.error(f"Cannot proccess image: {e}")
            await callback.message.edit_caption(
                caption=get_string(
                    "services.author_page_description", service.name, int(service.cost), service.cost_per, service.description
                ) if service.description else get_string(
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
            logger.error(f"Callback message not present or it is InaccessibleMessage: {callback.message}")
            return 
        new_keyboard = await parse_folder_keyboard(
            callback_data.path,
            callback_data.offset
        )
        try:
            await callback.message.edit_media(
                InputMediaPhoto(
                    media=FSInputFile('./src/res/images/empty_service.jpg'),
                    caption='Список доступных услуг'
                ),
                reply_markup=new_keyboard.as_markup()
            )
        except Exception as e:
            await callback.message.edit_caption(
                photo=FSInputFile('./src/res/images/empty_service.jpg'),
                caption='Список доступных услуг',
                reply_markup=new_keyboard.as_markup()
            )

    await callback.answer()