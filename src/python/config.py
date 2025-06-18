from pydantic import BaseModel, Field, ValidationError
from pathlib import Path
import tomli
import tomli_w
import shutil
from datetime import datetime
import os

os.makedirs("storage", exist_ok=True)


class DatabaseConfig(BaseModel):
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    user: str = Field(default="user")
    password: str = Field(default="password")
    database: str = Field(default="database")
    min_pool_size: int = Field(default=2)
    max_pool_size: int = Field(default=10)


class TelegramConfig(BaseModel):
    token: str = Field(default="0000000000:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    chat_whitelist: list[int] = Field(default_factory=list)
    parse_mode: str = Field(default="HTML")


class AppConfig(BaseModel):
    lang: str = Field(default="ru")
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)


CONFIG_PATH = Path("storage/config.toml")

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
        with CONFIG_PATH.open("rb") as f:
            data = tomli.load(f)
        return AppConfig(**data)
    except (tomli.TOMLDecodeError, ValidationError, TypeError) as e:
        print(f"Invalid config: {e}. Restoring defaults.")
        backup_corrupted_config()
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

def save_config(config: AppConfig):
    with CONFIG_PATH.open("wb") as f:
        tomli_w.dump(config.model_dump(), f)

config = load_config()
