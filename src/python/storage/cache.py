import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from zoneinfo import ZoneInfo

import aiofiles
import yaml
from pydantic import BaseModel, Field


class RemoveMessage(BaseModel):
    """
    Представляет сообщение, которое нужно автоматически удалить через определенное время.

    Используется для временных сообщений (эхо-команды, уведомления и т.д.), которые
    основной процесс сохраняет в кэш, а фоновая задача периодически проверяет и удаляет.

    Attributes:
        chat_id: ID чата, где находится сообщение
        message_id: ID сообщения для удаления
        create_time: Время создания сообщения (для расчета возраста)
    """
    chat_id: int
    message_id: int
    create_time: datetime = Field(default_factory=lambda: _get_now())


class PinMessage(BaseModel):
    """
    Представляет закрепленное справочное сообщение в чате.

    Используется для хранения информации о закрепленных сообщениях со справкой.
    При перезапуске бота эти сообщения обновляются актуальной информацией,
    сохраняя при этом свою закрепленность в чате.

    Attributes:
        chat_id: ID чата, где закреплено сообщение
        message_id: ID закрепленного сообщения
        lang: Язык справочного сообщения (для мультиязычной поддержки)
    """
    chat_id: int
    message_id: int
    lang: str


def _get_logger():
    """Отложенный импорт logger для избежания циклических зависимостей."""
    from python.logger import logger
    return logger


def _get_timezone() -> ZoneInfo | None:
    """Получить временную зону из конфига."""
    from python.storage.config import config
    if config and config.timezone:
        return ZoneInfo(config.timezone)
    return None


def _get_now() -> datetime:
    """Получить текущее время с учетом временной зоны из конфига."""
    tz = _get_timezone()
    return datetime.now(tz)


class CacheStorage(BaseModel):
    """
    Хранилище для временных сообщений и закрепленных справок с персистентностью в YAML.

    Основной процесс записывает сообщения для удаления, фоновая задача их удаляет.
    Автоматически обрабатывает поврежденные или отсутствующие файлы.

    Attributes:
        remove_messages: Список сообщений для автоматического удаления
        help_pin_messages: Список закрепленных справочных сообщений
        path: Путь к файлу кэша
    """

    remove_messages: List[RemoveMessage] = Field(default_factory=list)
    help_pin_messages: List[PinMessage] = Field(default_factory=list)
    path: Path = Path("cache.yaml")

    def __init__(self, path: Optional[str | Path] = None, **data):
        """
        Инициализация кэша.

        Note:
            Для асинхронной инициализации файла вызовите async_init() отдельно.
        """
        super().__init__(**data)
        if path:
            self.path = Path(path)

    async def async_init(self):
        """Асинхронная инициализация - создание файла кэша, если он не существует."""
        logger = _get_logger()
        if not self.path.exists():
            logger.info(f"Cache file does not exist, creating: {self.path}")
            await self.save()

    @staticmethod
    async def from_file(path: str = "cache.yaml") -> "CacheStorage":
        """
        Создать экземпляр CacheStorage и загрузить данные из YAML файла.

        Если файл поврежден или некорректен, он будет сохранен в бэкап и заменен новым.

        Args:
            path: Путь к файлу кэша

        Returns:
            Загруженный экземпляр CacheStorage
        """
        logger = _get_logger()
        logger.debug(f"Loading cache from file: {path}")
        storage = CacheStorage(path=Path(path))
        await storage.load()
        return storage

    async def load(self) -> None:
        """
        Загрузить данные из файла кэша.

        Если файл не существует - создает новый пустой.
        Если файл поврежден - создает бэкап и начинает с чистого листа.
        """
        logger = _get_logger()

        if not self.path.exists():
            logger.warning(f"Cache file not found: {self.path}, creating new one")
            await self.save()
            return

        try:
            # Асинхронное чтение файла
            async with aiofiles.open(self.path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = yaml.safe_load(content) or {}

            # Десериализация данных в модели Pydantic
            self.remove_messages = [RemoveMessage(**m) for m in data.get("remove_messages", [])]
            self.help_pin_messages = [PinMessage(**p) for p in data.get("pin_help_messages", [])]

            logger.info(
                f"Cache loaded: {len(self.remove_messages)} removable messages, "
                f"{len(self.help_pin_messages)} pinned messages"
            )
        except Exception as e:
            # При любой ошибке - сохраняем поврежденный файл в бэкап
            backup_path = self._make_backup_path()
            shutil.move(self.path, backup_path)
            logger.error(f"Invalid cache file backed up to: {backup_path}", e)

            # Начинаем с пустого кэша
            self.remove_messages = []
            self.help_pin_messages = []
            await self.save()

    def _make_backup_path(self) -> Path:
        """
        Сгенерировать путь для бэкапа с временной меткой.

        Returns:
            Path к бэкап-файлу в том же каталоге с временной меткой
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.path.stem}_backup_{timestamp}{self.path.suffix}"
        return self.path.with_name(backup_name)

    async def save(self) -> None:
        """
        Сохранить текущее состояние кэша в YAML файл.

        Raises:
            Exception: При ошибке сохранения файла
        """
        logger = _get_logger()

        try:
            # Убеждаемся, что директория существует
            self.path.parent.mkdir(parents=True, exist_ok=True)

            # Сериализация данных в YAML
            yaml_content = yaml.safe_dump(
                {
                    "remove_messages": [m.model_dump() for m in self.remove_messages],
                    "pin_help_messages": [p.model_dump() for p in self.help_pin_messages],
                },
                allow_unicode=True,
                sort_keys=False,
                indent=2,
            )

            # Асинхронная запись в файл
            async with aiofiles.open(self.path, "w", encoding="utf-8") as f:
                await f.write(yaml_content)

            logger.debug(f"Cache saved to {self.path}")
        except Exception as e:
            logger.error(f"Failed to save cache to {self.path}", e)
            raise

    async def insert_message(self, chat_id: int, message_id: int, stamp: Optional[datetime] = None) -> None:
        """
        Добавить сообщение в список для автоматического удаления.

        Вызывается основным процессом при отправке временных сообщений.

        Args:
            chat_id: ID чата с сообщением
            message_id: ID сообщения для удаления
            stamp: Время создания (если None - используется текущее время)
        """
        logger = _get_logger()

        if stamp is None:
            stamp = _get_now()

        msg = RemoveMessage(
            chat_id=chat_id, message_id=message_id, create_time=stamp
        )
        self.remove_messages.append(msg)
        logger.debug(f"Inserted message: chat_id={chat_id}, message_id={message_id}")

    def get_old_messages(self, delta: int) -> List[RemoveMessage]:
        """
        Получить все сообщения старше указанного количества секунд.

        Используется фоновой задачей, которая раз в минуту проверяет устаревшие сообщения.
e
        Args:
            delta: Возраст сообщения в секундах (например, 600 для удаления через 10 минут)

        Returns:
            Список сообщений, которые нужно удалить
        """
        logger = _get_logger()

        now = datetime.now(timezone.utc)
        old_messages = [m for m in self.remove_messages if (now - m.create_time).total_seconds() > delta]

        if old_messages:
            logger.debug(f"Found {len(old_messages)} old messages (delta={delta}s)")

        return old_messages

    # Предполагается, что RemoveMessage — это dataclass или модель с полем message_id
    # from python.storage.cache import RemoveMessage  # если нужно

    async def delete_messages(self, *messages: RemoveMessage) -> None:
        """
        Удалить сообщения из списка после их удаления в Telegram.

        Вызывается фоновой задачей после успешного удаления сообщений.

        Args:
            *messages: Объекты RemoveMessage, которые нужно удалить из кэша
        """
        logger = _get_logger()

        if not messages:
            return

        # Преобразуем в set для быстрого поиска (по message_id)
        message_ids_to_remove = {msg.message_id for msg in messages}
        initial_count = len(self.remove_messages)

        # Фильтруем список, оставляя только те, которых нет в переданных
        self.remove_messages = [
            m for m in self.remove_messages
            if m.message_id not in message_ids_to_remove
        ]
        deleted_count = initial_count - len(self.remove_messages)

        await self.save()

        if deleted_count > 0:
            removed_ids = [msg.message_id for msg in messages]
            logger.info(f"Deleted {deleted_count} messages: {removed_ids}", messages)
        else:
            incoming_ids = [msg.message_id for msg in messages]
            logger.warning(f"No messages found to delete: {incoming_ids}", messages)

    async def add_pin_message(self, chat_id: int, message_id: int, lang: str) -> None:
        """
        Добавить закрепленное справочное сообщение в список (если его еще нет).

        Используется при создании нового закрепленного сообщения со справкой.
        При перезапуске бота эти сообщения обновляются актуальной информацией.

        Args:
            chat_id: ID чата с закрепленным сообщением
            message_id: ID закрепленного сообщения
            lang: Язык справки (для мультиязычности)
        """
        logger = _get_logger()

        # Проверка на дубликаты
        for pin in self.help_pin_messages:
            if pin.chat_id == chat_id and pin.message_id == message_id:
                logger.debug(f"Pin message already exists: chat_id={chat_id}, message_id={message_id}")
                return

        self.help_pin_messages.append(PinMessage(
            chat_id=chat_id, message_id=message_id, lang=lang
        ))
        await self.save()
        logger.info(f"Added pin message: chat_id={chat_id}, message_id={message_id}, lang={lang}")

    async def remove_pin_message(self, chat_id: int, message_id: int) -> None:
        """
        Удалить закрепленное сообщение из списка.

        Используется при откреплении или удалении справочного сообщения.

        Args:
            chat_id: ID чата
            message_id: ID сообщения для удаления из списка
        """
        logger = _get_logger()

        initial_count = len(self.help_pin_messages)

        # Фильтруем список, удаляя совпадение по chat_id и message_id
        self.help_pin_messages = [
            pin for pin in self.help_pin_messages
            if not (pin.chat_id == chat_id and pin.message_id == message_id)
        ]
        removed = initial_count - len(self.help_pin_messages)

        await self.save()

        if removed > 0:
            logger.info(f"Removed pin message: chat_id={chat_id}, message_id={message_id}")
        else:
            logger.warning(f"Pin message not found: chat_id={chat_id}, message_id={message_id}")


async def init_cache():
    """
    Инициализировать глобальный экземпляр кэша.

    Должна быть вызвана при старте приложения перед использованием кэша.

    Raises:
        Exception: При ошибке загрузки кэша
    """
    global cache
    logger = _get_logger()
    logger.info("Initializing cache storage")
    try:
        cache = await CacheStorage.from_file("storage/cache.yaml")
        logger.info("Cache storage initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize cache storage", e)
        raise


# Глобальный экземпляр кэша (инициализируется через init_cache())
cache: Optional[CacheStorage] = None
