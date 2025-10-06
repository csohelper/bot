from pydantic import BaseModel, Field, ValidationError
from pathlib import Path
import shutil
from datetime import datetime
import os
import yaml

os.makedirs("storage", exist_ok=True)


class DatabaseConfig(BaseModel):
    host: str = Field(default="postgres")
    port: int = Field(default=5432)
    user: str = Field(default="postgres")
    password: str = Field(default="examplepassword")
    database: str = Field(default="mydatabase")
    min_pool_size: int = Field(default=2)
    max_pool_size: int = Field(default=10)


class ChatConfig(BaseModel):
    owner: int = Field(default=0)
    chat_id: int = Field(default=-1000000000000)
    admin_chat_id: int = Field(default=-1000000000000)
    hype_chat_id: int = Field(default=-1000000000000)
    admin_lang: str = Field(default="ru")
    default_lang: str = Field(default="en")


class TelegramConfig(BaseModel):
    token: str = Field(default="0000000000:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    parse_mode: str = Field(default="HTML")


class AnecdoteConfig(BaseModel):
    enabled: bool = Field(default=False)
    gemini_token: str = Field(default="your_gemini_token_here")
    buffer_size: int = Field(default=30)
    buffer_check_time: int = Field(default=30)
    antiflood_time: int = Field(default=30)


class RedisConfig(BaseModel):
    enabled: bool = Field(default=False)
    url: str = Field(default="redis://redis:6379")
    decode_responses: bool = Field(default=True)


class RefuserConfig(BaseModel):
    enabled: bool = Field(default=False)
    request_life_hours: int = Field(default=48)
    refuser_check_time: int = Field(default=10 * 60)


class LoggerConfig(BaseModel):
    console_level: str = Field(default='info')
    file_level: str = Field(default='debug')
    aiogram_level: str = Field(default='info')


class BlacklistedChat(BaseModel):
    chat_id: int = Field()
    topics: list[int | None] | None = Field(default=None)


class AppConfig(BaseModel):
    admin_lang: str = Field(default="ru")
    timezone: str = Field(default="Europe/Moscow")
    logger: LoggerConfig = Field(default_factory=LoggerConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis_config: RedisConfig = Field(default_factory=RedisConfig)
    anecdote: AnecdoteConfig = Field(default_factory=AnecdoteConfig)
    chat_config: ChatConfig = Field(default_factory=ChatConfig)
    refuser: RefuserConfig = Field(default_factory=RefuserConfig)
    blacklisted: list[BlacklistedChat] = Field(default_factory=list)


CONFIG_PATH = Path("storage/config.yaml")

DEFAULT_CONFIG = AppConfig()


def backup_corrupted_config():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = CONFIG_PATH.with_name(f"{CONFIG_PATH.stem}_backup_{timestamp}{CONFIG_PATH.suffix}")
    shutil.copy(CONFIG_PATH, backup_path)
    print(f"Backup created: {backup_path}")


def load_config() -> AppConfig:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}

        config = AppConfig(**raw_data)

        if config.model_dump() != raw_data:
            save_config(config)

        return config

    except (yaml.YAMLError, ValidationError, TypeError) as e:
        print(f"Invalid config: {e}. Restoring defaults.")
        backup_corrupted_config()
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG


def save_config(config: AppConfig):
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        yaml.dump(config.model_dump(), f, allow_unicode=True, sort_keys=False)


config = load_config()
