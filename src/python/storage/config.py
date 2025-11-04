import traceback

from pydantic import BaseModel, Field, ValidationError
from pathlib import Path
import shutil
from datetime import datetime
import os
import yaml
import aiofiles

os.makedirs("storage", exist_ok=True)


class DatabaseConfig(BaseModel):
    """
    Конфигурация подключения к PostgreSQL базе данных.

    Attributes:
        host: Хост базы данных (обычно имя контейнера в Docker)
        port: Порт PostgreSQL (стандартный 5432)
        user: Имя пользователя БД
        password: Пароль пользователя БД
        database: Название базы данных
        min_pool_size: Минимальный размер пула соединений
        max_pool_size: Максимальный размер пула соединений
    """
    host: str = Field(default="postgres")
    port: int = Field(default=5432)
    user: str = Field(default="postgres")
    password: str = Field(default="examplepassword")
    database: str = Field(default="mydatabase")
    min_pool_size: int = Field(default=2)
    max_pool_size: int = Field(default=10)


class AdminTopics(BaseModel):
    """
    Топики (темы) в админском чате для категоризации уведомлений.

    В Telegram чат может быть разбит на топики для структурирования информации.

    Attributes:
        debug: Топик для логов и отладочной информации
        join: Топик для заявок на вступление в основной чат
        service: Топик для служебных уведомлений
    """
    debug: int | None = Field(default=None)
    join: int | None = Field(default=None)
    service: int | None = Field(default=None)


class AdminConfig(BaseModel):
    """
    Конфигурация административного чата.

    Админский чат - место, куда стекаются ошибки, заявки и служебная информация.

    Attributes:
        chat_id: ID административного чата
        chat_lang: Язык для сообщений в админском чате
        topics: Топики для разных типов уведомлений
    """
    chat_id: int = Field(default=-1000000000000)
    chat_lang: str = Field(default="ru")
    topics: AdminTopics = Field(default_factory=AdminTopics)


class ChatConfig(BaseModel):
    """
    Конфигурация основных чатов бота.

    Бот работает с тремя чатами:
    1. Основной чат - где работает бот
    2. Админский чат - для уведомлений и управления
    3. Хайповый чат - для пересылки анкет "крутой комнаты общежития"

    Attributes:
        owner: ID владельца бота
        owner_username: Username владельца
        chat_id: ID основного чата
        hype_chat_id: ID чата для пересылки хайповых анкет с оценками экспертов
        invite_link: Ссылка-приглашение в основной чат
        echo_auto_delete_secs: Время в секундах, через которое удаляются эхо-сообщения
        admin: Конфигурация админского чата
    """
    owner: int | None = Field(default=None)
    owner_username: str | None = Field(default=None)
    chat_id: int = Field(default=-1000000000000)
    hype_chat_id: int = Field(default=-1000000000000)
    invite_link: str | None = Field(default=None)
    echo_auto_delete_secs: int = Field(default=600)  # 10 минут по умолчанию
    admin: AdminConfig = Field(default_factory=AdminConfig)


class TelegramConfig(BaseModel):
    """
    Конфигурация подключения к Telegram Bot API.

    Attributes:
        token: Токен бота от BotFather
        parse_mode: Режим парсинга сообщений (HTML/Markdown)
        server: URL локального Telegram Bot API сервера (Nginx Proxy)
    """
    token: str | None = Field(default=None)
    parse_mode: str = Field(default="HTML")
    server: str = Field(default="http://telegram-bot-api:8081")


class AnecdoteConfig(BaseModel):
    """
    Конфигурация системы генерации анекдотов через Gemini AI.

    Attributes:
        enabled: Включена ли функция генерации анекдотов
        gemini_token: API токен для доступа к Gemini
        buffer_size: Размер буфера предгенерированных анекдотов
        buffer_check_time: Интервал проверки буфера в секундах
        antiflood_time: Антифлуд - минимальное время между запросами в секундах
    """
    enabled: bool = Field(default=False)
    gemini_token: str = Field(default="your_gemini_token_here")
    buffer_size: int = Field(default=30)
    buffer_check_time: int = Field(default=30)
    antiflood_time: int = Field(default=30)


class RedisConfig(BaseModel):
    """
    Конфигурация подключения к Redis для кеширования.

    Attributes:
        enabled: Использовать ли Redis
        url: URL подключения к Redis
        decode_responses: Автоматически декодировать ответы в строки
    """
    enabled: bool = Field(default=False)
    url: str = Field(default="redis://redis:6379")
    decode_responses: bool = Field(default=True)


class RefuserConfig(BaseModel):
    """
    Конфигурация системы обработки заявок на вступление в чат.

    Attributes:
        enabled: Включена ли система обработки заявок
        request_life_hours: Время жизни заявки в часах
        refuser_check_time: Интервал проверки заявок в секундах (по умолчанию 10 минут)
    """
    enabled: bool = Field(default=False)
    request_life_hours: int = Field(default=48)
    refuser_check_time: int = Field(default=10 * 60)


class LoggerConfig(BaseModel):
    """
    Конфигурация системы логирования.

    Attributes:
        console_level: Уровень логирования для консоли (info/debug/warning/error)
        file_level: Уровень логирования для файла
        aiogram_level: Уровень логирования для aiogram библиотеки
        json_level: Уровень логирования для JSON логов
        backup_limit: Количество сохраняемых бэкапов лог-файлов (0 = без ограничений)
    """
    console_level: str = Field(default='info')
    file_level: str = Field(default='debug')
    aiogram_level: str = Field(default='info')
    json_level: str = Field(default='error')
    backup_limit: int = Field(default=0)


class BlacklistedChat(BaseModel):
    """
    Чат или топики чата, где бот не должен работать.

    В основном чате некоторые топики открыты для написания, но бот там не работает.
    Если кто-то отправит команду боту в заблокированном топике - сообщение удаляется.

    Attributes:
        chat_id: ID чата
        topics: Список ID топиков, где бот не работает (None = весь чат заблокирован)
    """
    chat_id: int = Field()
    topics: list[int | None] | None = Field(default=None)


class AppConfig(BaseModel):
    """
    Главная конфигурация приложения, объединяющая все настройки.

    Attributes:
        timezone: Временная зона (альтернатива ENV переменной "TZ")
        logger: Настройки логирования
        telegram: Настройки Telegram подключения
        database: Настройки PostgreSQL
        redis_config: Настройки Redis
        anecdote: Настройки генерации анекдотов
        chat_config: Настройки чатов бота
        refuser: Настройки системы заявок
        blacklisted: Список заблокированных чатов/топиков
    """
    timezone: str | None = Field(default=None, description="Using timezone instead of ENV \"TZ\"")
    logger: LoggerConfig = Field(default_factory=LoggerConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis_config: RedisConfig = Field(default_factory=RedisConfig)
    anecdote: AnecdoteConfig = Field(default_factory=AnecdoteConfig)
    chat_config: ChatConfig = Field(default_factory=ChatConfig)
    refuser: RefuserConfig = Field(default_factory=RefuserConfig)
    blacklisted: list[BlacklistedChat] = Field(default_factory=list)


# Путь к файлу конфигурации
CONFIG_PATH = Path("storage/config.yaml")

# Дефолтная конфигурация для первого запуска
DEFAULT_CONFIG = AppConfig()


def backup_corrupted_config():
    """
    Создать бэкап поврежденного конфига.

    Синхронная функция для надежности при критических ошибках.
    Создает копию файла с временной меткой в том же каталоге.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S%z")
    backup_path = CONFIG_PATH.with_name(f"{CONFIG_PATH.stem}_backup_{timestamp}{CONFIG_PATH.suffix}")
    shutil.copy(CONFIG_PATH, backup_path)
    print(f"Corrupted config backed up to: {backup_path}")


async def load_config() -> AppConfig:
    """
    Загрузить конфигурацию из YAML файла асинхронно.

    Если файл не существует - создается дефолтный.
    Если файл поврежден - создается бэкап и восстанавливается дефолтный.
    Если структура изменилась - файл нормализуется и пересохраняется.

    Returns:
        Загруженная или дефолтная конфигурация
    """

    if not CONFIG_PATH.exists():
        print(f"Config file not found: {CONFIG_PATH}, creating default config")
        await save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    try:
        print(f"Loading config from: {CONFIG_PATH}")

        # Асинхронное чтение файла
        async with aiofiles.open(CONFIG_PATH, "r", encoding="utf-8") as f:
            content = await f.read()
            raw_data = yaml.safe_load(content) or {}

        # Валидация через Pydantic
        app_config = AppConfig(**raw_data)

        # Если структура изменилась (добавились новые поля с дефолтами) - пересохраняем
        if app_config.model_dump() != raw_data:
            print("Config structure updated, saving normalized version")
            await save_config(app_config)

        print("Config loaded successfully")
        return app_config

    except (yaml.YAMLError, ValidationError, TypeError):
        # При ошибке парсинга или валидации - восстанавливаем дефолтный конфиг
        print(f"Invalid config file, restoring defaults")
        traceback.print_exc()
        backup_corrupted_config()
        await save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    except Exception:
        # При любой другой ошибке - тоже восстанавливаем дефолтный
        print(f"Unexpected error loading config")
        traceback.print_exc()
        backup_corrupted_config()
        await save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG


async def save_config(app_config: AppConfig):
    """
    Сохранить конфигурацию в YAML файл асинхронно.

    Args:
        app_config: Конфигурация для сохранения

    Raises:
        Exception: При ошибке записи в файл
    """

    try:
        print(f"Saving config to: {CONFIG_PATH}")

        # Сериализация в YAML
        yaml_content = yaml.dump(
            app_config.model_dump(),
            allow_unicode=True,
            sort_keys=False
        )

        # Асинхронная запись
        async with aiofiles.open(CONFIG_PATH, "w", encoding="utf-8") as f:
            await f.write(yaml_content)

        print("Config saved successfully")
    except Exception as e:
        print(f"Failed to save config to {CONFIG_PATH}", e)
        raise


async def init_config() -> AppConfig:
    """
    Инициализировать конфигурацию приложения.

    Должна быть вызвана при старте приложения.

    Returns:
        Загруженная конфигурация

    Raises:
        Exception: При критической ошибке инициализации
    """
    print("Initializing application config")
    try:
        cfg = await load_config()
        print("Application config initialized successfully")
        return cfg
    except Exception as e:
        print("Failed to initialize application config", e)
        raise


# Глобальный экземпляр конфигурации (инициализируется через init_config())
config: AppConfig | None = None
