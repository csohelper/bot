from pathlib import Path
from typing import Any

import yaml

__locale_dir = Path("src/res/strings/locale")

__locales = {}

for file in __locale_dir.glob("*.yaml"):
    with file.open("r", encoding="utf-8") as f:
        __stem = file.stem
        load = yaml.safe_load(f)
        for __lang in __stem.split('_'):
            __locales[__lang] = load


def __get_locale_string(locale: str, key: str, *args: Any, **kwargs: Any) -> str | None:
    """
    Получает строку по пути в локализации и подставляет переданные аргументы.

    :param locale: Локализация
    :param key: Путь через точку, например "greetings.hello"
    :param args: Аргументы для подстановки по порядку
    :param kwargs: Именованные аргументы для подстановки
    :return: Отформатированная строка, найденная в соответсвующей локали
    """
    keys = key.split(".")
    value = __locales.get(locale)
    try:
        for key in keys:
            value = value[key]
    except KeyError:
        return None
    if isinstance(value, str):
        return value.format(*args, **kwargs)
    else:
        raise RuntimeError("Isn't string")


def get_string(locale: str | None, key: str, *args: Any, **kwargs: Any) -> str | None:
    """
    Получает строку по пути в локализации и подставляет переданные аргументы.
    Если не будет найдена - будет возвращено из default локали

    :param locale: Локализация
    :param key: Путь через точку, например "greetings.hello"
    :param args: Аргументы для подстановки по порядку
    :param kwargs: Именованные аргументы для подстановки
    :return: Отформатированная строка, найденная в соответсвующей локали
    """
    if locale is None:
        locale = "default"
    result = __get_locale_string(locale, key, *args, **kwargs)
    if result is None:
        result = __get_locale_string("default", key, *args, **kwargs)
    return result


def __get_locale_object(locale: str, path: str) -> Any | None:
    keys = path.split(".")
    value = __locales.get(locale)
    try:
        for key in keys:
            value = value[key]
    except KeyError:
        return None
    return value


def list_langs() -> list[str]:
    langs = list(__locales.keys())
    langs.remove("default")
    return langs


def get_object(locale: str | None, key: str) -> Any | None:
    if locale is None:
        locale = "default"
    result = __get_locale_object(locale, key)
    if result is None:
        result = __get_locale_object("default", key)
    return result


def __get_locale_strings(locale: str | None, path: str, *args: Any) -> list[str] | None:
    """
    Получает строку по пути и подставляет переданные аргументы.

    :param path: Путь через точку, например "greetings.hello"
    :param args: Аргументы для подстановки по порядку
    :return: Отформатированная строка
    """
    keys = path.split(".")
    value = __locales.get(locale)
    try:
        for key in keys:
            value = value[key]
    except KeyError:
        return None
    if isinstance(value, list) and len(value) > 0 and isinstance(value[0], str):
        return [x.format(*args) for x in value]
    else:
        raise RuntimeError("Is't string list")


def get_strings(locale: str | None, key: str, *args: Any) -> list[str] | None:
    if locale is None:
        locale = "default"
    result = __get_locale_strings(locale, key, *args)
    if result is None:
        result = __get_locale_strings("default", key, *args)
    return result
