import asyncio
import datetime
import random
from dataclasses import dataclass

from aiogram import Router, F

from ..storage.config import config, save_config
from ..storage.strings import get_string, get_strings
from aiogram.types import Message
from aiogram.filters import Command
from .. import utils

router = Router()


@dataclass(frozen=True)
class EchoCommand:
    command: str
    text: list[str]
    response: str


commands = [
    EchoCommand("index", ["индекс"], 'echo_commands.index'),
    EchoCommand("address", ["адрес", "адресс", "адресочек"], 'echo_commands.address'),
    EchoCommand("director", ["заведующий", "заведующая", "завед", "заведа"], 'echo_commands.director'),
    EchoCommand(
        "commandant",
        ["коменда", "комендант", "командант", "командантка", "комменда", "коммендант", "коммандант", "коммандантка"],
        'echo_commands.commandant'
    ),
    EchoCommand(
        "jko",
        ["жко", "жк", "жилищно коммунальный", "жилищно коммунальный отдел", "жилищно-коммунальный отдел"],
        'echo_commands.jko'
    ),
    EchoCommand("ed", ["ед", "единый деканат", "деканат"], 'echo_commands.ed'),
    EchoCommand("hr", ["отдел кадров"], 'echo_commands.hr'),
    EchoCommand("soft", ["софт", "программы", "программное обеспечение", "ПО"], 'echo_commands.soft'),
    EchoCommand("library", ["библиотека"], 'echo_commands.library'),
    EchoCommand("shower", ["душ"], 'echo_commands.shower'),
    EchoCommand("kitchen", ["кухня"], 'echo_commands.kitchen'),
    EchoCommand("polyclinic", ["поликлиника"], 'echo_commands.polyclinic'),
    EchoCommand("accounting", ["бухгалтерия"], 'echo_commands.accounting'),
    EchoCommand("deanit", ["деканат ит"], 'echo_commands.deanery.it'),
    EchoCommand("deanrit", ["деканат рит"], 'echo_commands.deanery.rit'),
    EchoCommand("deannacs", ["деканат сисс"], 'echo_commands.deanery.nacs'),
    EchoCommand("deancais", ["деканат кииб"], 'echo_commands.deanery.cais'),
    EchoCommand("deandeamc", ["деканат цэимк"], 'echo_commands.deanery.deamc'),
]


def make_handler(command: EchoCommand):
    @router.message(Command(command.command))
    @router.message(lambda message, cmd=command: message.text and message.text.lower() in cmd.text)
    async def echo_command_handler(message: Message) -> None:
        await message.reply(get_string(command.response))

    return echo_command_handler


for command in commands:
    make_handler(command)


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
    await message.reply(get_string('echo_commands.help'))


@router.message(Command("mei"))
@router.message(lambda message: message.text and message.text.lower() in ["мэи", "меи"])
async def command_mei_handler(message: Message) -> None:
    await message.reply(
        random.choice(
            get_strings('echo_commands.mei')
        )
    )


@router.message(Command("meishniky"))
@router.message(lambda message: message.text and message.text.lower() in ["мэишники", "меишники"])
async def command_meishniky_handler(message: Message) -> None:
    await message.reply(
        random.choice(
            get_strings('echo_commands.meishniky')
        )
    )


@router.message(Command("mai"))
@router.message(lambda message: message.text and message.text.lower() in ["маи"])
async def command_mai_handler(message: Message) -> None:
    await message.reply(
        random.choice(
            get_strings('echo_commands.mai')
        )
    )


@router.message(Command("maishniki"))
@router.message(lambda message: message.text and message.text.lower() in ["маишники", "маёвцы"])
async def command_maishniky_handler(message: Message) -> None:
    await message.reply(
        random.choice(
            get_strings('echo_commands.maishniky')
        )
    )


@router.message(Command("week"))
@router.message(lambda message: message.text and message.text.lower() in ["неделя"])
async def command_week_handler(message: Message) -> None:
    week_number = utils.get_week_number(datetime.datetime.now())
    await message.reply(
        get_string(
            'echo_commands.week',
            get_strings('echo_commands.week_types_up_down')[week_number % 2],
            get_strings('echo_commands.week_types_even')[week_number % 2],
            week_number
        )
    )


@router.message(lambda message: message.text and message.text.lower() in ["заведущий", "заведущая"])
async def command_week_handler(message: Message) -> None:
    await message.reply(get_string(
        'echo_commands.incorrect_lang'
    ))
