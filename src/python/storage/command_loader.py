from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict

import yaml
from pydantic import BaseModel, Field
import aiofiles

import python.logger as logger_module
from python.storage.strings import list_langs, get_string

# Путь к файлу с описанием команд и их конфигурацией
__path = 'src/res/strings/commands_info.yaml'


class TimeInfoModel(BaseModel):
    """
    Модель для описания времени работы организации/сервиса.

    Используется в эхо-командах для отображения графика работы.
    При отправке команды алгоритм рассчитывает сколько осталось до открытия/закрытия.

    Attributes:
        key: Ключ для локализованного описания (например, "working_status")
        time: Строка с временем работы в формате для парсинга (например, "9:00-18:00")
    """
    key: str = Field(default='working_status')
    time: str = Field()


class CycleInfoModel(BaseModel):
    """
    Модель для циклической ротации изображений.

    Картинки отправляются по кругу: первый раз - первая, второй раз - вторая, и т.д.
    Когда список заканчивается - начинается сначала.

    Attributes:
        name: Название цикла для идентификации
        files: Список файлов для циклической отправки
    """
    name: str = Field()
    files: list["ImageInfoModel"] = Field(default_factory=list)

    @staticmethod
    def to_cyclefileinfo(original: "CycleInfoModel") -> "CycleFileInfo":
        """Конвертировать Pydantic модель в immutable dataclass."""
        return CycleFileInfo(
            original.name,
            [ImageInfoModel.to_imagefileinfo(x) for x in original.files]
        )


class RandomInfoModel(BaseModel):
    """
    Модель для случайной выборки изображений.

    При каждой отправке команды выбирается случайное изображение из списка.
    Индексы не меняются по порядку, а выбираются рандомно.

    Attributes:
        name: Название группы для идентификации
        files: Список файлов для случайной выборки
    """
    name: str = Field()
    files: list["ImageInfoModel"] = Field(default_factory=list)

    @staticmethod
    def to_randomfileinfo(original: "RandomInfoModel") -> "RandomFileInfo":
        """Конвертировать Pydantic модель в immutable dataclass."""
        return RandomFileInfo(
            original.name,
            [ImageInfoModel.to_imagefileinfo(x) for x in original.files]
        )


class ImageInfoModel(BaseModel):
    """
    Модель описания одного изображения или вложенной структуры изображений.

    Может быть:
    - Простым файлом (file)
    - Циклом изображений (cycle)
    - Случайной выборкой (random)

    Attributes:
        file: Путь к простому файлу изображения
        cycle: Вложенный цикл изображений
        random: Вложенная случайная выборка
    """
    file: Optional[str] = Field(default=None)
    cycle: Optional[CycleInfoModel] = Field(default=None)
    random: Optional[RandomInfoModel] = Field(default=None)

    @staticmethod
    def to_imagefileinfo(original: "ImageInfoModel") -> "ImageFileInfo":
        """
        Конвертировать Pydantic модель в immutable dataclass.

        Рекурсивно обрабатывает вложенные структуры cycle и random.
        """
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
    """
    Модель коллекции изображений для эхо-команды.

    Attributes:
        caption_above: True = подпись над изображением, False = подпись под изображением
        files: Список изображений (могут быть простыми, циклами или случайными)
    """
    caption_above: bool = Field(default=False)
    files: List[ImageInfoModel] = Field(default_factory=list)


class EchoCommandModel(BaseModel):
    """
    Модель эхо-команды - автоматического ответа на триггеры.

    Эхо-команды отправляют заготовленные сообщения с картинками по триггерным словам.
    Могут содержать информацию о времени работы организаций.

    Attributes:
        name: Название команды (идентификатор)
        message: Путь к локализованному тексту сообщения
        times: Список времен работы (для вставки в сообщение)
        images: Набор изображений для отправки с командой
    """
    name: str = Field()
    message: str = Field()
    times: List[TimeInfoModel] = Field(default_factory=list)
    images: Optional[ImagesInfoModel] = Field(default_factory=ImagesInfoModel)


class CommandsInfoModel(BaseModel):
    """
    Главная модель со всей информацией о командах бота.

    Attributes:
        triggers: Словарь триггеров: {название_команды: [список_триггерных_слов]}
        commands_list: Список команд для отображения в меню бота
        echo_commands: Список всех эхо-команд с их конфигурацией
    """
    triggers: Dict[str, List[str]] = Field(default_factory=dict)
    commands_list: List[str] = Field(default_factory=list)
    echo_commands: List[EchoCommandModel] = Field(default_factory=list)


async def __load_commands() -> CommandsInfoModel:
    """
    Загрузить информацию о командах из YAML файла асинхронно.

    Returns:
        Загруженная информация о командах

    Raises:
        FileNotFoundError: Если файл не найден
        Exception: При ошибке парсинга файла
    """
    try:
        logger_module.logger.debug(f"Loading commands info from: {__path}")

        if not Path(__path).exists():
            logger_module.logger.error(f"Commands info file not found: {__path}")
            raise FileNotFoundError(f"Commands info file not found: {__path}")

        # Асинхронное чтение файла
        async with aiofiles.open(__path, "r", encoding="utf-8") as f:
            content = await f.read()
            raw_data = yaml.safe_load(content) or {}

        # Валидация через Pydantic
        commands_info = CommandsInfoModel(**raw_data)

        logger_module.logger.info(
            f"Commands info loaded: {len(commands_info.commands_list)} commands, "
            f"{len(commands_info.echo_commands)} echo commands, "
            f"{len(commands_info.triggers)} trigger groups"
        )

        return commands_info

    except Exception as e:
        logger_module.logger.error(f"Failed to load commands info from {__path}", e)
        raise


# Глобальный экземпляр информации о командах (инициализируется асинхронно)
__commands_info: CommandsInfoModel | None = None


async def init_commands_info():
    """
    Инициализировать систему информации о командах.

    Должна быть вызвана при старте приложения перед использованием команд.

    Raises:
        Exception: При критической ошибке загрузки
    """
    global __commands_info
    logger_module.logger.info("Initializing commands info")
    try:
        __commands_info = await __load_commands()
        logger_module.logger.info("Commands info initialized successfully")
    except Exception as e:
        logger_module.logger.error("Failed to initialize commands info", e)
        raise


def _ensure_initialized():
    """
    Проверить, что система команд инициализирована.

    Raises:
        RuntimeError: Если init_commands_info() не была вызвана
    """
    if __commands_info is None:
        if logger_module.logger:  # Только если logger_module.logger инициализирован
            logger_module.logger.error("Commands info not initialized. Call init_commands_info() first.")
        raise RuntimeError("Commands info not initialized. Call init_commands_info() first.")


@dataclass(frozen=True)
class TelegramCommand:
    """
    Immutable представление команды для Telegram меню.

    Attributes:
        name: Название команды (без слэша)
        description: Локализованное описание команды
    """
    name: str
    description: str


@dataclass(frozen=True)
class TelegramCommandsInfo:
    """
    Набор команд для конкретного языка.

    Attributes:
        lang: Код языка (или None для дефолтного)
        commands_list: Список команд с описаниями на этом языке
    """
    lang: str | None
    commands_list: List[TelegramCommand]


def get_telegram_commands_list() -> List[TelegramCommandsInfo]:
    """
    Получить списки команд для всех доступных языков.

    Используется для установки меню команд в Telegram для каждого языка.

    Returns:
        Список команд для каждого языка + дефолтный набор (None)
    """
    _ensure_initialized()

    logger_module.logger.debug("Generating Telegram commands list for all languages")

    # Получаем команды для всех известных языков
    langs = list_langs()
    result = [__get_lang_telegram_commands_info(lang) for lang in langs]

    # Добавляем дефолтный набор команд (для языков не из списка)
    result.append(__get_lang_telegram_commands_info(None))

    logger_module.logger.debug(f"Generated commands list for {len(result)} languages")
    return result


def __get_lang_telegram_commands_info(lang: str | None) -> TelegramCommandsInfo:
    """
    Получить информацию о командах для конкретного языка.

    Пропускает команды без описания в данном языке.

    Args:
        lang: Код языка или None для дефолтного

    Returns:
        Информация о командах для указанного языка
    """
    _ensure_initialized()

    command_list = []
    skipped = 0

    # Для каждой команды из списка получаем локализованное описание
    for command_name in __commands_info.commands_list:
        description = get_string(lang, f"commands_description.{command_name}")

        # Если описание отсутствует или пустое - пропускаем команду
        if not description or description.strip() == "":
            logger_module.logger.warning(
                f"Command '{command_name}' in language '{lang}' has no description. Skipping."
            )
            skipped += 1
            continue

        command_list.append(
            TelegramCommand(
                command_name,
                description
            )
        )

    if skipped > 0:
        logger_module.logger.debug(f"Skipped {skipped} commands without description for language '{lang}'")

    logger_module.logger.debug(f"Generated {len(command_list)} commands for language '{lang}'")
    return TelegramCommandsInfo(lang, command_list)


@dataclass(frozen=True)
class TimeInfo:
    """
    Immutable информация о времени работы.

    Attributes:
        key: Ключ локализации для описания
        time: Строка времени для парсинга
    """
    key: str
    time: str


@dataclass(frozen=True)
class ImageFileInfo:
    """
    Immutable информация об изображении.

    Может содержать либо простой файл, либо вложенную структуру (cycle/random).

    Attributes:
        file: Путь к файлу или None
        cycle: Вложенный цикл или None
        random: Вложенная случайная выборка или None
    """
    file: Optional[str]
    cycle: Optional["CycleFileInfo"]
    random: Optional["RandomFileInfo"]


@dataclass(frozen=True)
class CycleFileInfo:
    """
    Immutable информация о цикле изображений.

    Attributes:
        name: Идентификатор цикла
        files: Список изображений для циклической отправки
    """
    name: str
    files: list["ImageFileInfo"]


@dataclass(frozen=True)
class RandomFileInfo:
    """
    Immutable информация о случайной выборке изображений.

    Attributes:
        name: Идентификатор группы
        files: Список изображений для случайной выборки
    """
    name: str
    files: list["ImageFileInfo"]


@dataclass(frozen=True)
class ImageInfo:
    """
    Immutable информация о коллекции изображений.

    Attributes:
        caption_above: Позиция подписи (True = сверху, False = снизу)
        files: Список изображений
    """
    caption_above: bool
    files: List[ImageFileInfo]


@dataclass(frozen=True)
class EchoCommand:
    """
    Immutable полное описание эхо-команды для использования в боте.

    Attributes:
        name: Идентификатор команды
        message_path: Путь к локализованному тексту сообщения
        images: Информация об изображениях или None
        times: Список времен работы для вставки в текст
        triggers: Список триггерных слов, активирующих команду
    """
    name: str
    message_path: str
    images: Optional[ImageInfo]
    times: List[TimeInfo]
    triggers: List[str]


def get_all_triggers(command: str) -> List[str]:
    """
    Получить все триггерные слова для конкретной команды.

    Триггеры используются для активации эхо-команд при упоминании ключевых слов.

    Args:
        command: Название команды

    Returns:
        Список уникальных триггерных слов (пустой список если триггеров нет)
    """
    _ensure_initialized()

    if command not in __commands_info.triggers:
        logger_module.logger.debug(f"No triggers found for command '{command}'")
        return []

    # Фильтруем None и убираем дубликаты
    triggers = list(filter(
        None, set(
            __commands_info.triggers[command]
        )
    ))

    logger_module.logger.debug(f"Found {len(triggers)} triggers for command '{command}'")
    return triggers


def get_echo_commands() -> List[EchoCommand]:
    """
    Получить все эхо-команды с их полной конфигурацией.

    Конвертирует Pydantic модели в immutable dataclass для безопасного использования.

    Returns:
        Список всех эхо-команд с изображениями, временами работы и триггерами
    """
    _ensure_initialized()

    logger_module.logger.debug("Generating echo commands list")

    echo_commands = [
        EchoCommand(
            info.name,
            info.message,
            # Конвертируем изображения если они есть
            ImageInfo(
                info.images.caption_above,
                [
                    ImageInfoModel.to_imagefileinfo(file) for file in info.images.files
                ]
            ) if info.images else None,
            # Конвертируем времена работы
            [TimeInfo(time.key, time.time) for time in info.times],
            # Получаем все триггеры для команды
            get_all_triggers(info.name)
        )
        for info in __commands_info.echo_commands
    ]

    logger_module.logger.debug(f"Generated {len(echo_commands)} echo commands")
    return echo_commands
