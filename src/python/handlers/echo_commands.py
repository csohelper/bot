import asyncio
import datetime
import random
from aiogram import Router, F

from ..storage.config import config, save_config
from ..storage.strings import get_string, get_strings
from aiogram.types import Message
from aiogram.filters import Command
from .. import utils

router = Router()


@router.message(Command("start", "help", "commands", "comands"))
@router.message(lambda message: message.text and message.text.lower() in [
    "начать", "помощь", "хелп", "команды", "комманды", "список", "помоги", "я долбаеб", "я долбоебка", "я долбаёб",
    "я долбоёбка", "я долбаебка", "я долбаёбка"
])
async def command_help_handler(message: Message) -> None:
    if message.text == "/start" and message.chat.type == "private" and config.chat_config.owner == 0:
        await message.reply(get_string('echo_commands.first_start'))
        config.chat_config.owner = message.from_user.id
        save_config(config)
        return
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.help'))


@router.message(Command("index"))
@router.message(lambda message: message.text and message.text.lower() in ["индекс"])
async def command_index_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.index'))


@router.message(Command("address"))
@router.message(lambda message: message.text and message.text.lower() in ["адрес", "адресс", "адресочек"])
async def command_address_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.address'))


@router.message(Command("director"))
@router.message(
    lambda message: message.text and message.text.lower() in ["заведующий", "заведующая", "завед", "заведа"])
async def command_director_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.director'))


@router.message(Command("commandant"))
@router.message(
    lambda message: message.text and message.text.lower() in ["коменда", "комендант", "командант", "командантка",
                                                              "комменда", "коммендант", "коммандант", "коммандантка"])
async def command_commandant_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(
        get_string('echo_commands.commandant')
    )


@router.message(Command("jko"))
@router.message(lambda message: message.text and message.text.lower() in ["жко", "жк", "жилищно коммунальный",
                                                                          "жилищно коммунальный отдел",
                                                                          "жилищно-коммунальный отдел"])
async def command_jko_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.jko'))


@router.message(Command("ed"))
@router.message(lambda message: message.text and message.text.lower() in ["ед", "единый деканат", "деканат"])
async def command_ed_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.ed'))


@router.message(Command("hr"))
@router.message(lambda message: message.text and message.text.lower() in ["отдел кадров"])
async def command_hr_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.hr'))


@router.message(Command("soft"))
@router.message(
    lambda message: message.text and message.text.lower() in ["софт", "программы", "программное обеспечение", "ПО"])
async def command_soft_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.soft'))


BAD_WORDS = ["сосать", "долбаёб", "шлюха", "мразь", "сука"]


@router.message(
    F.chat.type.in_(["group", "supergroup"]),  # только группы и супергруппы
    Command("sosat")
)
@router.message(
    F.chat.type.in_(["group", "supergroup"]),  # только группы и супергруппы
    F.text.lower().in_(BAD_WORDS)
)
async def command_sosat_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.sosat'))


@router.message(Command("library"))
@router.message(lambda message: message.text and message.text.lower() in ["библиотека"])
async def command_library_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.library'))


@router.message(Command("stolovka"))
@router.message(lambda message: message.text and message.text.lower() in ["столовка"])
async def command_ulk_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(get_string('echo_commands.cafe_ulk'))


@router.message(Command("mei"))
@router.message(lambda message: message.text and message.text.lower() in ["мэи", "меи"])
async def command_mei_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(
        random.choice(
            get_strings('echo_commands.mei')
        )
    )


@router.message(Command("meishniky"))
@router.message(lambda message: message.text and message.text.lower() in ["мэишники", "меишники"])
async def command_meishniky_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(
        random.choice(
            get_strings('echo_commands.meishniky')
        )
    )


@router.message(Command("mai"))
@router.message(lambda message: message.text and message.text.lower() in ["маи"])
async def command_mai_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(
        random.choice(
            get_strings('echo_commands.mai')
        )
    )


@router.message(Command("maishniki"))
@router.message(lambda message: message.text and message.text.lower() in ["маишники", "маёвцы"])
async def command_maishniky_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(
        random.choice(
            get_strings('echo_commands.maishniky')
        )
    )


@router.message(Command("shower"))
@router.message(lambda message: message.text and message.text.lower() in ["душ"])
async def command_shower_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(
        get_string('echo_commands.shower')
    )


@router.message(Command("kitchen"))
@router.message(lambda message: message.text and message.text.lower() in ["кухня"])
async def command_kitchen_handler(message: Message) -> None:
    await asyncio.sleep(1)
    await message.reply(
        get_string('echo_commands.kitchen')
    )


@router.message(Command("week"))
@router.message(lambda message: message.text and message.text.lower() in ["неделя"])
async def command_week_handler(message: Message) -> None:
    await asyncio.sleep(1)
    week_number = utils.get_week_number(datetime.datetime.now())
    await message.reply(
        get_string(
            'echo_commands.week',
            get_strings('echo_commands.week_types_up_down')[week_number % 2],
            get_strings('echo_commands.week_types_even')[week_number % 2],
            week_number
        )
    )

# @router.message(Command("washing"))
# @router.message(lambda message: message.text and message.text.lower() in ["стиралка", "машинки"])
# async def command_washing_handler(message: Message) -> None:
#     await message.reply(
#         get_string('echo_commands.washing')
#     )
