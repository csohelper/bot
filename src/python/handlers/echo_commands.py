import asyncio
import datetime
import random
from dataclasses import dataclass, field
from typing import List

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.payload import decode_payload

from .services_handlers.add_service_commands import on_addservice
from .services_handlers.join_service import on_accept_join_process
from ..logger import logger
from ..storage.config import config, save_config
from ..storage.strings import get_string, get_strings
from aiogram.types import Message
from aiogram.filters import Command, CommandStart, CommandObject
from .. import utils
from ..storage.times import get_time_status

router = Router()


@dataclass(frozen=True)
class WorkingKey:
    time_address: str
    key: str = 'working_status'


@dataclass(frozen=True)
class EchoCommand:
    command: str
    text: list[str]
    response: str
    working_status: List[WorkingKey] = field(default_factory=list)


commands = [
    EchoCommand("index", ["индекс"], 'echo_commands.index'),
    EchoCommand("address", ["адрес", "адресс", "адресочек"], 'echo_commands.address'),
    EchoCommand(
        "director", ["заведующий", "заведующая", "завед", "заведа"], 'echo_commands.director',
        [WorkingKey('dorm.director')]
    ),
    EchoCommand(
        "commandant",
        ["коменда", "комендант", "командант", "командантка", "комменда", "коммендант", "коммандант", "коммандантка"],
        'echo_commands.commandant'
    ),
    EchoCommand(
        "jko",
        ["жко", "жк", "жилищно коммунальный", "жилищно коммунальный отдел", "жилищно-коммунальный отдел"],
        'echo_commands.jko', [WorkingKey('university.jko')]
    ),
    EchoCommand(
        "hr", ["отдел кадров"], 'echo_commands.hr',
        [WorkingKey('university.hr.working'), WorkingKey('university.hr.certificate', 'working_status_certificate')]
    ),
    EchoCommand("soft", ["софт", "программы", "программное обеспечение", "ПО"], 'echo_commands.soft'),
    EchoCommand(
        "library", ["библиотека"], 'echo_commands.library',
        [WorkingKey('university.library.working'), WorkingKey('university.library.clients', 'working_status_clients')]
    ),
    EchoCommand("shower", ["душ"], 'echo_commands.shower', [WorkingKey('dorm.shower')]),
    EchoCommand("kitchen", ["кухня"], 'echo_commands.kitchen', [WorkingKey('dorm.kitchen')]),
    EchoCommand("polyclinic", ["поликлиника"], 'echo_commands.polyclinic', [WorkingKey('polyclinic')]),
    EchoCommand("accounting", ["бухгалтерия"], 'echo_commands.accounting', [WorkingKey('university.accounting')]),

    EchoCommand("dean", ["деканат"], 'echo_commands.deanery.default'),
    EchoCommand("ed", ["ед", "единый деканат"], 'echo_commands.deanery.ed', [WorkingKey('university.deans.ed')]),
    EchoCommand("deanit", ["деканат ит"], 'echo_commands.deanery.it', [WorkingKey('university.deans.it')]),
    EchoCommand("deanrit", ["деканат рит"], 'echo_commands.deanery.rit', [WorkingKey('university.deans.rit')]),
    EchoCommand("deannacs", ["деканат сисс"], 'echo_commands.deanery.nacs', [WorkingKey('university.deans.nacs')]),
    EchoCommand("deancais", ["деканат кииб"], 'echo_commands.deanery.cais', [WorkingKey('university.deans.cais')]),
    EchoCommand("deandeamc", ["деканат цэимк"], 'echo_commands.deanery.deamc'),
    EchoCommand(
        "deanforeign", ["иностранный деканат", "иностранный отдел"], 'echo_commands.deanery.foreign',
        [WorkingKey('university.deans.foreign')]
    ),

    EchoCommand("depritres", ["кафедра ртс"], 'echo_commands.departments.rit.res'),
    EchoCommand("depritreac", ["кафедра рос"], 'echo_commands.departments.rit.reac'),
    EchoCommand("depritelect", ["кафедра электроники"], 'echo_commands.departments.rit.electronics'),
    EchoCommand("deprittasb", ["кафедра тизв"], 'echo_commands.departments.rit.tasb'),
    EchoCommand("depritratsan", ["кафедра сисрт"], 'echo_commands.departments.rit.ratsan'),
    EchoCommand("deprittec", ["кафедра тэц"], 'echo_commands.departments.rit.tec'),
    EchoCommand("depritphys", ["кафедра физики"], 'echo_commands.departments.rit.physics'),
    EchoCommand("depritteaa", ["кафедра тэдиа"], 'echo_commands.departments.rit.teaa'),

    EchoCommand("depitmcait", ["кафедра мкиит"], 'echo_commands.departments.it.mcait'),
    EchoCommand("depitmcis", ["кафедра кис"], 'echo_commands.departments.it.cis'),
    EchoCommand("depitnitas", ["кафедра ситис"], 'echo_commands.departments.it.nitas'),
    EchoCommand("depitma", ["кафедра матанализ"], 'echo_commands.departments.it.ma'),
    EchoCommand("depitinf", ["кафедра информатика"], 'echo_commands.departments.it.informatics'),
    EchoCommand("depitpe", ["кафедра физвосп"], 'echo_commands.departments.it.pe'),
    EchoCommand("depitaai", ["кафедра пии"], 'echo_commands.departments.it.aai'),
    EchoCommand("depitsp", ["кафедра сп"], 'echo_commands.departments.it.sp'),

    EchoCommand("depmts", ["кафедра мтс"], 'echo_commands.departments.nacs.mts'),
    EchoCommand("depgts", ["кафедра нтс"], 'echo_commands.departments.nacs.gts'),
    EchoCommand("depgnass", ["кафедра ссиск"], 'echo_commands.departments.nacs.gnass'),
    EchoCommand("depmsami", ["кафедра мсиии"], 'echo_commands.departments.nacs.msami'),
    EchoCommand("depgtc", ["кафедра отс"], 'echo_commands.departments.nacs.gtc'),

    EchoCommand("depedet", ["кафедра тэод"], 'echo_commands.departments.cais.edet'),
    EchoCommand("depis", ["кафедра иб"], 'echo_commands.departments.cais.is'),
    EchoCommand("depismaa", ["кафедра исуиа"], 'echo_commands.departments.cais.ismaa'),
    EchoCommand("deptcs", ["кафедра бтк"], 'echo_commands.departments.cais.tcs'),
    EchoCommand("depptaam", ["кафедра твипм"], 'echo_commands.departments.cais.ptaam'),
    EchoCommand("depelsap", ["кафедра эбжиэ"], 'echo_commands.departments.cais.elsap'),
    EchoCommand("depbmt", ["кафедра овп"], 'echo_commands.departments.cais.bmt'),

    EchoCommand("depdat", ["кафедра ЦТР"], 'echo_commands.departments.deamc.dat'),
    EchoCommand("depsrapr", ["кафедра СРиСО"], 'echo_commands.departments.deamc.srapr'),
    EchoCommand("depdemabt", ["кафедра ЦЭУиБТ"], 'echo_commands.departments.deamc.demabt'),
    EchoCommand("depphaic", ["кафедра ФИиМК"], 'echo_commands.departments.deamc.phaic'),
    EchoCommand("depfor", ["кафедра ИНО"], 'echo_commands.departments.deamc.for'),
    EchoCommand("depbcs", ["кафедра БИ"], 'echo_commands.departments.deamc.bcs')
]


def build_kwargs(working_status: List[WorkingKey]) -> dict[str, str]:
    return {
        wk.key: get_time_status(wk.time_address)
        for wk in working_status
    }


def make_handler(command: EchoCommand):
    @router.message(Command(command.command))
    @router.message(lambda message, cmd=command: message.text and message.text.lower() in cmd.text)
    async def echo_command_handler(message: Message) -> None:
        await message.reply(get_string(
            command.response,
            **build_kwargs(command.working_status)
        ))

    return echo_command_handler


for command in commands:
    make_handler(command)


@router.message(CommandStart(deep_link=True))
async def command_start_handler(message: Message, command: CommandObject, state: FSMContext) -> None:
    args = command.args
    payload = decode_payload(args)
    logger.debug(payload)

    match payload:
        case 'addservice':
            await on_addservice(message, state)
        case _ if payload == get_string("user_service.greeting_button_start_payload"):
            await on_accept_join_process(message, state)
        case _:
            logger.error(f"Can't handle start payload - Args: {args}, Payload: {payload}")


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.reply(get_string('echo_commands.start'))

    if message.chat.type == "private" and config.chat_config.owner == 0:
        await message.answer(get_string('echo_commands.first_start'))
        config.chat_config.owner = message.from_user.id
        save_config(config)
        return


@router.message(Command("help", "commands", "comands"))
@router.message(lambda message: message.text and message.text.lower() in [
    "начать", "помощь", "хелп", "команды", "комманды", "список", "помоги", "я долбаеб", "я долбоебка", "я долбаёб",
    "я долбоёбка", "я долбаебка", "я долбаёбка"
])
async def command_help_handler(message: Message) -> None:
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
