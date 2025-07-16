import urllib.parse
from aiogram import Bot, Router
from aiogram import types
from aiogram.filters import Command, StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InaccessibleMessage, InlineKeyboardButton, InputMediaPhoto, Message, FSInputFile, BufferedInputFile
from attr import dataclass
from aiogram.utils.keyboard import InlineKeyboardBuilder

from python.logger import logger
from python.storage import services_repository
import base64
import io

from ..storage.strings import get_string


_bot_username: str
_bot: Bot


async def init(bot_username: str, bot: Bot):
    global _bot_username, _bot
    _bot_username = bot_username
    _bot = bot
    await services_repository.init_database_module()


router = Router()


class ServicesCallbackFactory(CallbackData, prefix="services"):
    path: str
    is_service: bool = False
    offset: int = 0


PAGE_SIZE = 5


async def parse_folder_keyboard(path: str, offset=0) -> tuple[InlineKeyboardBuilder, int, int]:
    services = await services_repository.get_service_list(path)
    builder = InlineKeyboardBuilder()
    logger.debug(f"{path}:", services)

    if path == "/":
        builder.row(
            InlineKeyboardButton(
                text=get_string("services.add_button.title"),
                url=get_string("services.add_button.url_placeholder", _bot_username)
            )
        )

    if len(services) > PAGE_SIZE:
        l = services[offset:offset+PAGE_SIZE]
    else:
        l = services

    for service in l:
        if service.is_folder:
            button_path = service.folder_dest
            text = get_string("services.folder_button", service.name)
        else:
            button_path = service.service_id
            text = get_string(
                "services.service_button", 
                service.name, service.cost, service.cost_per,
                service.username
            )

        if button_path is not None:
            builder.row(
                InlineKeyboardButton(
                    text = text,
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
                    text=get_string("services.prev_button"),
                    callback_data=ServicesCallbackFactory(
                        path=path,
                        offset=offset - PAGE_SIZE
                    ).pack()
                )
            )
        if offset + PAGE_SIZE < len(services):
            row.append(
                InlineKeyboardButton(
                    text=get_string("services.next_button"),
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
            text=get_string("services.back_button"),
            callback_data=ServicesCallbackFactory(
                path=parent_path
            ).pack()
        ))

    return builder, offset // PAGE_SIZE + 1, len(services) // PAGE_SIZE + 1


@router.message(Command("services"))
@router.message(lambda message: message.text and message.text.lower() in ["услуги"])
async def command_services_handler(message: Message) -> None:
    builder, page, pages = await parse_folder_keyboard("/")

    caption_lines = [get_string("services.folder_caption.header").strip()]
    if pages > 1:
        caption_lines.append(
            get_string(
                'services.folder_caption.page',
                page, pages
            ).strip()
        )

    await message.reply_photo(
        photo=FSInputFile('./src/res/images/empty_service.jpg'),
        caption='\n'.join(caption_lines),
        reply_markup=builder.as_markup()
    )


@router.callback_query(ServicesCallbackFactory.filter())
async def callbacks_num_change_fab(
    callback: types.CallbackQuery, 
    callback_data: ServicesCallbackFactory
) -> None:
    if not callback.message:
        return
    if callback_data.is_service:
        service = await services_repository.find_service(int(callback_data.path))
        if service is None:
            return
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=get_string("services.go_button.title"),
            url=get_string(
                "services.go_button.url_placeholder", 
                service.username, 
                urllib.parse.quote(service.name)
            )
        ))
        builder.row(InlineKeyboardButton(
            text=get_string("services.back_button"),
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
        new_keyboard, page, pages = await parse_folder_keyboard(
            callback_data.path,
            callback_data.offset
        )

        caption_lines = [get_string("services.folder_caption.header").strip()]
        strip_path = callback_data.path.strip("/")
        if strip_path:
            caption_lines.append(
                get_string('services.folder_caption.folder.sep').join(
                    get_string(
                        'services.folder_caption.folder.title', part
                    ) for part in strip_path.split("/")
                ).strip()
            )
        if pages > 1:
            caption_lines.append(
                get_string(
                    'services.folder_caption.page',
                    page, pages
                ).strip()
            )
        
        try:
            await callback.message.edit_media(
                InputMediaPhoto(
                    media=FSInputFile('./src/res/images/empty_service.jpg'),
                    caption='\n'.join(caption_lines)
                ),
                reply_markup=new_keyboard.as_markup()
            )
        except Exception as e:
            await callback.message.edit_caption(
                photo=FSInputFile('./src/res/images/empty_service.jpg'),
                caption='\n'.join(caption_lines),
                reply_markup=new_keyboard.as_markup()
            )

    await callback.answer()


class AddServiceStates(StatesGroup):
    choosing_name_state = State()
    choosing_description_state = State()
    choosing_cost_state = State()
    choosing_cost_per_state = State()
    choosing_picture_state = State()


@router.message(StateFilter(None), Command("addservice"))
async def on_addservice(message: Message, state: FSMContext) -> None:
    await message.reply(
        text=get_string('services.add_command.greeting')
    )
    await state.set_state(AddServiceStates.choosing_name_state)

@router.message(
    AddServiceStates.choosing_name_state
)
async def on_name_chosen(message: Message, state: FSMContext) -> None:
    if not message.text or not 4 <= len(message.text) <= 25:
        await message.reply(
            text=get_string('services.add_command.incorrect_name')
        )
        return

    await state.update_data(
        name=message.text
    )
    await message.reply(
        text=get_string('services.add_command.choose_description')
    )
    await state.set_state(AddServiceStates.choosing_description_state)


@router.message(
    AddServiceStates.choosing_description_state
)
async def on_description_chosen(message: Message, state: FSMContext) -> None:
    if message.text is None or message.text.strip() == '':
        await message.reply('Incorrect description. Send /empty or some text')
        return
    elif message.text == '/empty':
        await state.update_data(
            description=None
        )
    else:
        await state.update_data(
            description=message.text
        )
    await message.reply(
        text=get_string('services.add_command.choose_cost')
    )
    await state.set_state(AddServiceStates.choosing_cost_state)


@router.message(
    AddServiceStates.choosing_cost_state
)
async def on_cost_chosen(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.isdigit() or int(message.text) <= 0:
        await message.reply(
            text=get_string('services.add_command.cost_not_int')
        )
        return

    await state.update_data(
        cost=int(message.text)
    )
    await message.reply(
        text=get_string('services.add_command.choose_cost_per')
    )
    await state.set_state(AddServiceStates.choosing_cost_per_state)


@router.message(
    AddServiceStates.choosing_cost_per_state
)
async def on_cost_per_chosen(message: Message, state: FSMContext) -> None:
    if not message.text or not (1 <= len(message.text) <= 6):
        await message.reply(
            text=get_string('services.add_command.cost_per_incorrect')
        )
        return

    await state.update_data(
        cost_per=message.text
    )
    await message.reply(
        text=get_string('services.add_command.choose_picture')
    )
    await state.set_state(AddServiceStates.choosing_picture_state)


@router.message(
    AddServiceStates.choosing_picture_state
)
async def on_picture_chosen(message: Message, state: FSMContext) -> None:
    if message.text == '/empty':
        await state.update_data(
            image=None
        )
        await process_create_service(message, state)
        await state.clear()
        return

    if not message.photo:
        await message.reply(
            get_string("services.add_command.not_photo_and_empty")
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

    await process_create_service(message, state)
    await state.clear()

async def process_create_service(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data['image']:
        image_bytes = base64.b64decode(data['image'])
        image_stream = io.BytesIO(image_bytes)
        media = BufferedInputFile(image_stream.read(), filename=f"preview.jpg")
    else: 
        media = FSInputFile('./src/res/images/empty_service.jpg')

    desc = data['description']
    caption = get_string(
        'services.add_command.preview',
        data['name'],
        data['cost'], data['cost_per'],
        desc if desc else get_string('services.service_no_description')
    )

    await message.reply_photo(
        photo=media,
        caption=caption
    )
    print(state)