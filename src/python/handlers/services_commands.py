import asyncio
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from attr import dataclass
from ..strings import get_string


@dataclass(frozen=True)
class Service:
    id: int
    path: str
    name: str
    cost: int
    cost_per: str
    url: str


services_list: list[Service] = [
    Service(
        id=0,
        path="/Печать",
        name="Цветная печать",
        cost=8,
        cost_per="лист",
        url="https://t.me/slavapmk?text=Привет%20я%20по%20поводу%20услуги"
    ),
    Service(
        id=1,
        path="/Печать",
        name="Ч/Б печать",
        cost=7,
        cost_per="лист",
        url="https://t.me/malish_jora?text=Привет%20я%20по%20поводу%20услуги"
    ),
    Service(
        id=2,
        path="/Общага",
        name="Заточка ножей",
        cost=200,
        cost_per="нож",
        url="https://t.me/olixandor?text=Привет%20я%20по%20поводу%20услуги"
    ),
    Service(
        id=3,
        path="/Общага",
        name="Клининг",
        cost=199,
        cost_per="секунда",
        url="https://t.me/krutoikaras?text=Привет%20я%20по%20поводу%20услуги"
    ),
    Service(
        id=4,
        path="/Общага/Учеба",
        name="Клининг",
        cost=1000,
        cost_per="день",
        url="https://t.me/gyndenovv?text=Привет%20я%20по%20поводу%20услуги"
    ),
]

@dataclass(frozen=True)
class ServiceItem:
    name: str
    is_folder: bool
    service_id: int | None = None
    folder_dest: str | None = None


print(services_list)

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

    if path != "/":
        path_split = path.strip("/").split("/")

        del path_split[-1]
        parent_path = "/" + "/".join(path_split)
        output.insert(
            0,
            ServiceItem(name="Назад", is_folder=True, folder_dest=parent_path)
        )

    return output


print("/:", get_service_list("/"))
print("/Общага:", get_service_list("/Общага"))
print("/Общага/Учеба:", get_service_list("/Общага/Учеба"))


router = Router()


@router.message(Command("services"))
@router.message(lambda message: message.text and message.text.lower() in ["услуги"])
async def command_services_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(
        get_string('echo_commands.uslugi_stub')
    )