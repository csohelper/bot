from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict

import yaml
from pydantic import BaseModel, Field

from python.logger import logger
from python.storage.strings import list_langs, get_string, get_object

__path = 'src/res/strings/commands_info.yaml'


class TimeInfoModel(BaseModel):
    key: str = Field(default='working_status')
    time: str = Field()


class ImagesInfoModel(BaseModel):
    caption_above: bool = Field(default=False)
    files: List[str] = Field(default_factory=list)


class EchoCommandModel(BaseModel):
    name: str = Field()
    message: str = Field()
    times: List[TimeInfoModel] = Field(default_factory=list)
    images: Optional[ImagesInfoModel] = Field(default_factory=ImagesInfoModel)


class CommandsInfoModel(BaseModel):
    triggers: Dict[str, List[str]] = Field(default_factory=dict)
    commands_list: List[str] = Field(default_factory=list)
    echo_commands: List[EchoCommandModel] = Field(default_factory=list)


def __load_commands():
    with Path(__path).open("r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f) or {}

    return CommandsInfoModel(**raw_data)


__commands_info = __load_commands()


@dataclass(frozen=True)
class TelegramCommand:
    name: str
    description: str


@dataclass(frozen=True)
class TelegramCommandsInfo:
    lang: str | None
    commands_list: List[TelegramCommand]


def get_telegram_commands_list() -> List[TelegramCommandsInfo]:
    langs = list_langs()
    result = [__get_lang_telegram_commands_info(lang) for lang in langs]
    result.append(__get_lang_telegram_commands_info(None))
    return result


def __get_lang_telegram_commands_info(lang: str | None) -> TelegramCommandsInfo:
    command_list = []
    for command_name in __commands_info.commands_list:
        description = get_string(lang, f"commands_description.{command_name}")
        if not description or description.strip() == "":
            logger.warning(f"Command {command_name} in {lang} has no description. Skipping.")
            continue
        command_list.append(
            TelegramCommand(
                command_name,
                description
            )
        )
    return TelegramCommandsInfo(lang, command_list)


@dataclass(frozen=True)
class TimeInfo:
    key: str
    time: str


@dataclass(frozen=True)
class ImageInfo:
    caption_above: bool
    files: List[str]


@dataclass(frozen=True)
class EchoCommand:
    name: str
    message_path: str
    images: Optional[ImageInfo]
    times: List[TimeInfo]
    triggers: List[str]


def get_all_triggers(command: str) -> List[str]:
    if command not in __commands_info.triggers:
        return []
    return list(filter(
        None, set(
            __commands_info.triggers[command]
        )
    ))


def get_echo_commands() -> List[EchoCommand]:
    return [
        EchoCommand(
            info.name, info.message,
            ImageInfo(
                info.images.caption_above,
                info.images.files
            ) if info.images else None,
            [TimeInfo(time.key, time.time) for time in info.times],
            get_all_triggers(info.name)
        )
        for info in __commands_info.echo_commands
    ]
