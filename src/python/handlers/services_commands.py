from aiogram import Router
from aiogram import types
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, Message, FSInputFile
from attr import dataclass
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..strings import get_string


bot_username: str


@dataclass(frozen=True)
class Service:
    id: int
    path: str
    name: str
    cost: int
    cost_per: str
    username: str
    description: str | None


services_list: list[Service] = [
    Service(
        id=0,
        path="/Печать",
        name="Цветная печать",
        cost=8,
        cost_per="лист",
        username="slavapmk",
        description="Сасал"
    ),
    Service(
        id=1,
        path="/Печать",
        name="Ч/Б печать",
        cost=7,
        cost_per="лист",
        username="malish_jora",
        description="Сасал"
    ),
    Service(
        id=2,
        path="/Общага",
        name="Заточка ножей",
        cost=200,
        cost_per="нож",
        username="olixandor",
        description="Сасал"
    ),
    Service(
        id=3,
        path="/Общага",
        name="Клининг",
        cost=199,
        cost_per="секунда",
        username="krutoikaras",
        description=None
    ),
    Service(
        id=4,
        path="/Учеба",
        name="Микронаушник",
        cost=1000,
        cost_per="день",
        username="gyndenovv",
        description=""
    ),
]

@dataclass(frozen=True)
class ServiceItem:
    name: str
    is_folder: bool
    service_id: int | None = None
    folder_dest: str | None = None


def get_service_list(path: str = "/") -> list[ServiceItem]:
    folders = set(
        ServiceItem(
            name=service.path.removeprefix(path).removeprefix("/"),
            is_folder=True,
            folder_dest=service.path
        ) for service in services_list if service.path != path and service.path.startswith(path) and "/" not in service.path.removeprefix(path).removeprefix("/")
    )
    items = list(
        ServiceItem(
            name=service.name,
            is_folder=False,
            service_id=service.id
        ) for service in services_list if service.path == path
    )
    output = list(folders) + items

    return output


router = Router()


class ServicesCallbackFactory(CallbackData, prefix="services"):
    path: str
    is_service: bool = False
    offset: int = 0


PAGE_SIZE = 2


async def parse_folder_keyboard(path: str, offset=0) -> InlineKeyboardBuilder:
    services = get_service_list(path)
    builder = InlineKeyboardBuilder()
    print(f"{path}:", services)

    builder.row(
        InlineKeyboardButton(
            text="Добавить услугу",
            url=f"https://t.me/{bot_username}?text=/addservice"
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


async def find_service(service_id: int) -> Service | None:
    """
    Stub for Future DB
    """
    for service in services_list:
        if service.id == service_id:
            return service
    return None


@router.callback_query(ServicesCallbackFactory.filter())
async def callbacks_num_change_fab(
    callback: types.CallbackQuery, 
    callback_data: ServicesCallbackFactory
) -> None:
    print("\n\n", callback_data)
    if not callback.message:
        return
    if callback_data.is_service:
        service = await find_service(int(callback_data.path))
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
                path=service.path
            ).pack()
        ))

        await callback.message.edit_caption(
            photo=FSInputFile('./src/res/images/empty_service.jpg'),
            caption=get_string(
                "services.author_page_description", service.name, service.cost, service.cost_per, service.description
            ) if service.description else get_string(
                "services.author_page", service.name, service.cost, service.cost_per
            ),
            reply_markup=builder.as_markup()
        )
    else:
        new_keyboard = await parse_folder_keyboard(
            callback_data.path,
            callback_data.offset
        )
        await callback.message.edit_caption(
            photo=FSInputFile('./src/res/images/empty_service.jpg'),
            caption='Список доступных услуг',
            reply_markup=new_keyboard.as_markup()
        )

    await callback.answer()