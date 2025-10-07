from os import path
from pathlib import Path
from typing import Any, List

import yaml
from pydantic import BaseModel, Field

from python.logger import logger

__info_path = 'src/res/strings/locale/lang.yaml'
__untranslatable_path = 'src/res/strings/locale/untranslatable.yaml'
__locale_dir = "src/res/strings/locale/lang"


class LangModel(BaseModel):
    file: str = Field()
    langs: List[str] = Field(default_factory=list)


class LangsInfoModel(BaseModel):
    default: str = Field(default='en')
    lang_files: List[LangModel] = Field(default_factory=list)


def __load_lang_info():
    with Path(__info_path).open("r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f) or {}

    return LangsInfoModel(**raw_data)


def __load_locales():
    result = {}
    for lang_file in __lang_info.lang_files:
        try:
            with open(path.join(__locale_dir, lang_file.file + ".yaml"), "r", encoding="utf-8") as f:
                load = yaml.safe_load(f)
                for lang in lang_file.langs:
                    result[lang] = load
        except FileNotFoundError:
            continue
    with Path(__untranslatable_path).open("r", encoding="utf-8") as f:
        load = yaml.safe_load(f)
        result["untranslatable"] = load
    return result


__lang_info = __load_lang_info()

__locales = __load_locales()


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


def get_string(locale: str | None, key: str, *args: str | int, **kwargs: str | int) -> str | None:
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
        locale = __lang_info.default
    result = __get_locale_string(locale, key, *args, **kwargs)
    if result is None and locale != __lang_info.default:
        result = __get_locale_string(__lang_info.default, key, *args, **kwargs)
        if result is not None:
            logger.debug(f"Using default locale for {locale}")
    if locale == __lang_info.default:
        logger.debug(f"Requested default {locale} locale")
    if result is None:
        result = __get_locale_string("untranslatable", key, *args, **kwargs)
    return result


def get_string_variants(key: str, *args: Any, **kwargs: Any) -> list[str]:
    langs = list(__locales.keys())
    return [
        s
        for lang in langs
        if (s := __get_locale_string(lang, key, *args, **kwargs)) is not None
    ]


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
    langs.remove("untranslatable")
    return langs


def get_object(locale: str | None, key: str) -> Any | None:
    if locale is None:
        locale = __lang_info.default
    result = __get_locale_object(locale, key)
    if result is None and locale != __lang_info.default:
        result = __get_locale_object(__lang_info.default, key)
    if result is None:
        result = __get_locale_object("untranslatable", key)
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
        locale = __lang_info.default
    result = __get_locale_strings(locale, key, *args)
    if result is None and locale != __lang_info.default:
        result = __get_locale_strings(__lang_info.default, key, *args)
    if result is None:
        result = __get_locale_strings("untranslatable", key, *args)
    return result
