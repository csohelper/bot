from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict

import yaml
from pydantic import BaseModel, Field

from python.logger import logger
from python.storage.strings import list_langs, get_string

__path = 'src/res/strings/commands_info.yaml'


class TimeInfoModel(BaseModel):
    key: str = Field(default='working_status')
    time: str = Field()


class CycleInfoModel(BaseModel):
    name: str = Field()
    files: list["ImageInfoModel"] = Field(default_factory=list)

    @staticmethod
    def to_cyclefileinfo(original: "CycleInfoModel") -> "CycleFileInfo":
        return CycleFileInfo(
            original.name,
            [ImageInfoModel.to_imagefileinfo(x) for x in original.files]
        )


class RandomInfoModel(BaseModel):
    name: str = Field()
    files: list["ImageInfoModel"] = Field(default_factory=list)

    @staticmethod
    def to_randomfileinfo(original: "RandomInfoModel") -> "RandomFileInfo":
        return RandomFileInfo(
            original.name,
            [ImageInfoModel.to_imagefileinfo(x) for x in original.files]
        )


class ImageInfoModel(BaseModel):
    file: Optional[str] = Field(default=None)
    cycle: Optional[CycleInfoModel] = Field(default=None)
    random: Optional[RandomInfoModel] = Field(default=None)

    @staticmethod
    def to_imagefileinfo(original: "ImageInfoModel") -> "ImageFileInfo":
        cycle: CycleInfoModel = original.cycle
        cycle_info: CycleFileInfo | None = None
        if cycle and len(cycle.files) != 0:
            cycle_info = CycleInfoModel.to_cyclefileinfo(cycle)

        random: RandomInfoModel = original.random
        random_info: RandomFileInfo | None = None
        if random and len(random.files) != 0:
            random_info = RandomInfoModel.to_randomfileinfo(random)

        return ImageFileInfo(
            original.file,
            cycle_info,
            random_info
        )


class ImagesInfoModel(BaseModel):
    caption_above: bool = Field(default=False)
    files: List[ImageInfoModel] = Field(default_factory=list)


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
class ImageFileInfo:
    file: Optional[str]
    cycle: Optional["CycleFileInfo"]
    random: Optional["RandomFileInfo"]


@dataclass(frozen=True)
class CycleFileInfo:
    name: str
    files: list["ImageFileInfo"]


@dataclass(frozen=True)
class RandomFileInfo:
    name: str
    files: list["ImageFileInfo"]


@dataclass(frozen=True)
class ImageInfo:
    caption_above: bool
    files: List[ImageFileInfo]


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
                [
                    ImageInfoModel.to_imagefileinfo(file) for file in info.images.files
                ]
            ) if info.images else None,
            [TimeInfo(time.key, time.time) for time in info.times],
            get_all_triggers(info.name)
        )
        for info in __commands_info.echo_commands
    ]
