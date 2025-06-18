import yaml
from typing import Any
from .config import config

with open(
    f'src/res/locale/{config.lang}.yaml', 'r', encoding='utf-8'
) as f:
    __strings = yaml.safe_load(f)


def get_string(path: str, *args: Any) -> str:
    """
    Получает строку по пути и подставляет переданные аргументы.
    
    :param path: Путь через точку, например "greetings.hello"
    :param args: Аргументы для подстановки по порядку
    :return: Отформатированная строка
    """
    keys = path.split(".")
    value = __strings
    for key in keys:
        value = value[key]
    return value.format(*args)