from os import path
from pathlib import Path
from typing import Any, List

import yaml
from pydantic import BaseModel, Field
import aiofiles

import python.logger as logger_module

# Пути к файлам локализации
__info_path = 'src/res/strings/locale/lang.yaml'  # Конфигурация языков
__untranslatable_path = 'src/res/strings/locale/untranslatable.yaml'  # Непереводимые строки
__locale_dir = "src/res/strings/locale/lang"  # Директория с файлами локализаций


class LangModel(BaseModel):
    """
    Модель описания файла локализации.

    Один файл может содержать переводы для нескольких языков.

    Attributes:
        file: Имя файла (без расширения .yaml)
        langs: Список кодов языков, которые содержит этот файл
    """
    file: str = Field()
    langs: List[str] = Field(default_factory=list)


class LangsInfoModel(BaseModel):
    """
    Модель конфигурации системы локализации.

    Определяет поведение при запросе разных языков и fallback логику.

    Attributes:
        none_lang: Язык по умолчанию, используемый когда язык не указан (null)
        unknown_lang: Fallback язык для неизвестных/неподдерживаемых языков
        priority_lang: Приоритетный язык - если строка не найдена в запрошенном языке,
                      ищется в этом языке перед поиском в untranslatable
        lang_files: Список файлов локализации для загрузки
    """
    none_lang: str = Field(default='ru')
    unknown_lang: str = Field(default='en')
    priority_lang: str = Field(default='ru')
    lang_files: List[LangModel] = Field(default_factory=list)


async def __load_lang_info() -> LangsInfoModel:
    """
    Загрузить конфигурацию системы локализации из YAML файла.

    Returns:
        Конфигурация языков

    Raises:
        FileNotFoundError: Если файл конфигурации не найден
        Exception: При ошибке парсинга
    """
    try:
        logger_module.logger.debug(f"Loading language info from: {__info_path}")

        if not Path(__info_path).exists():
            logger_module.logger.error(f"Language info file not found: {__info_path}")
            raise FileNotFoundError(f"Language info file not found: {__info_path}")

        # Асинхронное чтение файла
        async with aiofiles.open(__info_path, "r", encoding="utf-8") as f:
            content = await f.read()
            raw_data = yaml.safe_load(content) or {}

        # Валидация через Pydantic
        lang_info = LangsInfoModel(**raw_data)

        logger_module.logger.info(
            f"Language info loaded: none_lang={lang_info.none_lang}, "
            f"unknown_lang={lang_info.unknown_lang}, "
            f"priority_lang={lang_info.priority_lang}, "
            f"{len(lang_info.lang_files)} language files"
        )

        return lang_info

    except Exception as e:
        logger_module.logger.error(f"Failed to load language info from {__info_path}", e)
        raise


async def __load_locales(lang_info: LangsInfoModel) -> dict:
    """
    Загрузить все файлы локализации асинхронно.

    Загружает:
    1. Все языковые файлы из конфигурации
    2. Специальный файл "untranslatable" для непереводимых строк
       (например, системные команды, технические термины)

    Args:
        lang_info: Конфигурация с информацией о файлах локализации

    Returns:
        Словарь {язык: словарь_переводов}
    """
    result = {}
    loaded_count = 0
    failed_count = 0

    logger_module.logger.debug(f"Loading locale files from: {__locale_dir}")

    # Загрузка обычных языковых файлов
    for lang_file in lang_info.lang_files:
        file_path = path.join(__locale_dir, lang_file.file + ".yaml")
        try:
            if not Path(file_path).exists():
                logger_module.logger.warning(f"Locale file not found: {file_path}")
                failed_count += 1
                continue

            # Асинхронное чтение файла
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                load = yaml.safe_load(content)

            # Один файл может содержать переводы для нескольких языков
            for lang in lang_file.langs:
                result[lang] = load
                loaded_count += 1

            logger_module.logger.debug(
                f"Loaded locale file '{lang_file.file}' for languages: {', '.join(lang_file.langs)}"
            )

        except Exception as e:
            logger_module.logger.error(f"Failed to load locale file: {file_path}", e)
            failed_count += 1
            continue

    # Загрузка непереводимых строк
    # Эти строки используются как финальный fallback, если строка не найдена ни в каком языке
    try:
        logger_module.logger.debug(f"Loading untranslatable strings from: {__untranslatable_path}")

        if not Path(__untranslatable_path).exists():
            logger_module.logger.warning(f"Untranslatable file not found: {__untranslatable_path}")
        else:
            async with aiofiles.open(__untranslatable_path, "r", encoding="utf-8") as f:
                content = await f.read()
                load = yaml.safe_load(content)
            result["untranslatable"] = load
            logger_module.logger.debug("Untranslatable strings loaded")

    except Exception as e:
        logger_module.logger.error(f"Failed to load untranslatable strings from {__untranslatable_path}", e)

    logger_module.logger.info(
        f"Locales loaded: {loaded_count} languages successfully, "
        f"{failed_count} failed"
    )

    return result


# Глобальные переменные (инициализируются асинхронно)
__lang_info: LangsInfoModel | None = None  # Конфигурация системы локализации
__locales: dict | None = None  # Словарь всех загруженных переводов


async def init_strings():
    """
    Инициализировать систему локализации строк.

    Должна быть вызвана при старте приложения перед использованием любых функций локализации.

    Raises:
        Exception: При критической ошибке загрузки
    """
    global __lang_info, __locales

    logger_module.logger.info("Initializing string localization system")

    try:
        __lang_info = await __load_lang_info()
        __locales = await __load_locales(__lang_info)
        logger_module.logger.info("String localization system initialized successfully")
    except Exception as e:
        logger_module.logger.error("Failed to initialize string localization system", e)
        raise


def _ensure_initialized():
    """
    Проверить, что система локализации инициализирована.

    Raises:
        RuntimeError: Если init_strings() не была вызвана
    """
    if __lang_info is None or __locales is None:
        logger_module.logger.error("String system not initialized. Call init_strings() first.")
        raise RuntimeError("String system not initialized. Call init_strings() first.")


def __get_locale_string(locale: str, key: str, *args: Any, **kwargs: Any) -> str | None:
    """
    Получить строку из конкретной локали по ключу с форматированием.

    Внутренняя функция. Не выполняет fallback логику.

    Args:
        locale: Код языка
        key: Путь к строке через точку (например, "greetings.hello")
        args: Позиционные аргументы для форматирования строки
        kwargs: Именованные аргументы для форматирования строки

    Returns:
        Отформатированная строка или None если не найдена
    """
    _ensure_initialized()

    # Разбиваем путь на части
    keys = key.split(".")
    value = __locales.get(locale)

    # Навигация по вложенной структуре словаря
    try:
        for k in keys:
            value = value[k]
    except (KeyError, TypeError):
        logger_module.logger.debug(f"Key '{key}' not found in locale '{locale}'")
        return None

    # Проверяем что значение - строка
    if isinstance(value, str):
        try:
            # Форматируем строку с переданными аргументами
            return value.format(*args, **kwargs)
        except (KeyError, IndexError) as e:
            logger_module.logger.warning(f"Failed to format string for key '{key}' in locale '{locale}'", e)
            return value  # Возвращаем неотформатированную строку
    else:
        logger_module.logger.error(f"Value for key '{key}' in locale '{locale}' is not a string")
        raise RuntimeError("Isn't string")


def get_string(locale: str | None, key: str, *args: str | int | float | None, **kwargs: str | int) -> str | None:
    """
    Получить локализованную строку с автоматическим fallback.

    Логика поиска:
    1. Если locale is None → используется none_lang из конфига
    2. Если locale неизвестен → используется unknown_lang
    3. Поиск строки в запрошенной локали
    4. Если не найдена → поиск в priority_lang
    5. Если не найдена → поиск в untranslatable
    6. Если не найдена → возврат None

    Args:
        locale: Код языка или None для дефолтного
        key: Путь к строке через точку (например, "commands.help.text")
        args: Позиционные аргументы для форматирования
        kwargs: Именованные аргументы для форматирования

    Returns:
        Локализованная отформатированная строка или None

    Example:
        get_string("en", "welcome.message", name="John")
        # → "Welcome, John!"
    """
    _ensure_initialized()

    original_locale = locale

    # Обработка None → дефолтный язык
    if locale is None:
        logger_module.logger.trace(f"Requested None -> {__lang_info.none_lang} locale")
        locale = __lang_info.none_lang

    # Обработка неизвестного языка → fallback язык
    if locale not in __locales.keys():
        logger_module.logger.trace(f"Requested unknown {locale} -> {__lang_info.unknown_lang} locale")
        locale = __lang_info.unknown_lang

    # Попытка 1: Поиск в запрошенной локали
    result = __get_locale_string(locale, key, *args, **kwargs)

    # Попытка 2: Поиск в приоритетной локали
    if result is None:
        result = __get_locale_string(__lang_info.priority_lang, key, *args, **kwargs)
        if result is not None:
            logger_module.logger.trace(f"Requested {locale} -> Priority {__lang_info.priority_lang} locale")

    if result is not None:
        logger_module.logger.trace(f"Requested {locale} locale")

    # Попытка 3: Поиск в непереводимых строках
    if result is None:
        result = __get_locale_string("untranslatable", key, *args, **kwargs)
        if result is not None:
            logger_module.logger.trace(f"Requested {locale} -> untranslatable locale")

    # Если так и не нашли - логируем предупреждение
    if result is None:
        logger_module.logger.warning(f"String not found: locale='{original_locale}', key='{key}'")

    return result


def get_string_variants(key: str, *args: Any, **kwargs: Any) -> list[str]:
    """
    Получить все варианты строки из всех доступных языков.

    Используется для:
    - Проверки существования строки в разных языках
    - Проверки триггеров на всех языках

    Args:
        key: Путь к строке
        args: Позиционные аргументы для форматирования
        kwargs: Именованные аргументы для форматирования

    Returns:
        Список всех найденных вариантов строки (без дубликатов по содержимому)

    Example:
        get_string_variants("commands.start.trigger")
        # → ["старт", "start", "comenzar"]
    """
    _ensure_initialized()

    langs = list(__locales.keys())
    variants = [
        s
        for lang in langs
        if (s := __get_locale_string(lang, key, *args, **kwargs)) is not None
    ]

    logger_module.logger.debug(f"Found {len(variants)} variants for key '{key}' across {len(langs)} locales")
    return variants


def __get_locale_object(locale: str, string_key: str) -> Any | None:
    """
    Получить сырой объект из локали (не только строки).

    Внутренняя функция для получения словарей, списков и других структур.

    Args:
        locale: Код языка
        string_key: Путь к объекту через точку

    Returns:
        Объект любого типа или None
    """
    _ensure_initialized()

    keys = string_key.split(".")
    value = __locales.get(locale)

    try:
        for key in keys:
            value = value[key]
    except (KeyError, TypeError):
        logger_module.logger.debug(f"Object key '{string_key}' not found in locale '{locale}'")
        return None

    return value


def list_langs() -> list[str]:
    """
    Получить список всех доступных языковых кодов.

    Исключает специальную локаль "untranslatable".

    Returns:
        Список кодов языков (например, ["ru", "en", "es"])
    """
    _ensure_initialized()

    langs = list(__locales.keys())
    if "untranslatable" in langs:
        langs.remove("untranslatable")

    logger_module.logger.debug(f"Available languages: {', '.join(langs)}")
    return langs


def get_object(locale: str | None, key: str) -> Any | None:
    """
    Получить сырой объект из локали с fallback логикой.

    Аналогично get_string, но возвращает любой объект (dict, list, и т.д.),
    не только строки. Используется для получения структурированных данных.

    Логика fallback та же что у get_string.

    Args:
        locale: Код языка или None
        key: Путь к объекту

    Returns:
        Объект любого типа или None

    Example:
        get_object("en", "menu.items")
        # → {"home": {...}, "about": {...}}
    """
    _ensure_initialized()

    original_locale = locale

    # Обработка None и неизвестного языка
    if locale is None:
        logger_module.logger.trace(f"Requested None -> {__lang_info.none_lang} locale")
        locale = __lang_info.none_lang

    if locale not in __locales.keys():
        logger_module.logger.trace(f"Requested Unknown {locale} -> {__lang_info.unknown_lang} locale")
        locale = __lang_info.unknown_lang

    # Попытка 1: Запрошенная локаль
    result = __get_locale_object(locale, key)

    # Попытка 2: Приоритетная локаль
    if result is None:
        result = __get_locale_object(__lang_info.priority_lang, key)
        if result is not None:
            logger_module.logger.trace(f"Requested {locale} -> Priority {__lang_info.priority_lang} locale")

    if result is not None:
        logger_module.logger.trace(f"Requested {locale} locale")

    # Попытка 3: Непереводимые строки
    if result is None:
        result = __get_locale_object("untranslatable", key)
        if result is not None:
            logger_module.logger.trace(f"Requested {locale} -> untranslatable locale")

    if result is None:
        logger_module.logger.warning(f"Object not found: locale='{original_locale}', key='{key}'")

    return result


def __get_locale_strings(locale: str | None, string_key: str, *args: Any) -> list[str] | None:
    """
    Получить список строк из локали с форматированием.

    Внутренняя функция для работы со списками строк.

    Args:
        locale: Код языка
        string_key: Путь к списку строк
        args: Позиционные аргументы для форматирования каждой строки

    Returns:
        Список отформатированных строк или None
    """
    _ensure_initialized()

    keys = string_key.split(".")
    value = __locales.get(locale)

    try:
        for key in keys:
            value = value[key]
    except (KeyError, TypeError):
        logger_module.logger.debug(f"String list key '{string_key}' not found in locale '{locale}'")
        return None

    # Проверяем что это список строк
    if isinstance(value, list) and len(value) > 0 and isinstance(value[0], str):
        try:
            # Форматируем каждую строку в списке
            return [x.format(*args) for x in value]
        except (KeyError, IndexError) as e:
            logger_module.logger.warning(f"Failed to format string list for key '{string_key}' in locale '{locale}'", e)
            return value  # Возвращаем неотформатированный список
    else:
        logger_module.logger.error(f"Value for key '{string_key}' in locale '{locale}' is not a string list")
        raise RuntimeError("Isn't string list")


def get_strings(locale: str | None, key: str, *args: Any) -> list[str] | None:
    """
    Получить список локализованных строк с fallback логикой.

    Используется когда нужно получить массив строк (например, список вариантов ответа).
    Логика fallback та же что у get_string.

    Args:
        locale: Код языка или None
        key: Путь к списку строк
        args: Позиционные аргументы для форматирования

    Returns:
        Список строк или None

    Example:
        get_strings("en", "errors.validation", field="email")
        # → ["Invalid {field}", "{field} is required", ...]
    """
    _ensure_initialized()

    original_locale = locale

    # Обработка None и неизвестного языка
    if locale is None:
        logger_module.logger.trace(f"Requested None -> {__lang_info.none_lang} locale")
        locale = __lang_info.none_lang

    if locale not in __locales.keys():
        logger_module.logger.trace(f"Requested unknown {locale} -> {__lang_info.unknown_lang} locale")
        locale = __lang_info.unknown_lang

    # Попытка 1: Запрошенная локаль
    result = __get_locale_strings(locale, key, *args)

    # Попытка 2: Приоритетная локаль
    if result is None:
        result = __get_locale_strings(__lang_info.priority_lang, key, *args)
        if result is not None:
            logger_module.logger.trace(f"Requested {locale} -> Priority {__lang_info.priority_lang} locale")

    if result is not None:
        logger_module.logger.trace(f"Requested {locale} locale")

    # Попытка 3: Непереводимые строки
    if result is None:
        result = __get_locale_strings("untranslatable", key, *args)
        if result is not None:
            logger_module.logger.trace(f"Requested {locale} -> untranslatable locale")

    if result is None:
        logger_module.logger.warning(f"String list not found: locale='{original_locale}', key='{key}'")

    return result
