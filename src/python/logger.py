import inspect
import json
import logging
import os
import re
import traceback
import uuid
import zipfile
from datetime import datetime, date
from logging.handlers import TimedRotatingFileHandler
from typing import Any
from zoneinfo import ZoneInfo

TRACE_LEVEL = 5  # ниже DEBUG (10)
logging.addLevelName(TRACE_LEVEL, "TRACE")


def get_earliest_timestamp(base_dir: str, tz: ZoneInfo | None) -> datetime | None:
    if tz is None:
        tz = datetime.now().astimezone().tzinfo

    text_path = os.path.join(base_dir, "latest.log")
    json_path = os.path.join(base_dir, "latest.jsonl")
    timestamps = []

    # Парсинг .log
    if os.path.exists(text_path) and os.path.getsize(text_path) > 0:
        with open(text_path, "r", encoding="utf-8") as f:
            for line in f:
                m = re.search(r"(\d{2}\.\d{2}\.\d{4}) (\d{2}:\d{2}:\d{2}\.\d{3})([+-]\d{4})", line)
                if m:
                    date_str, time_str, tz_str = m.groups()
                    try:
                        dt = datetime.strptime(f"{date_str} {time_str}{tz_str}", "%d.%m.%Y %H:%M:%S.%f%z")
                        dt = dt.astimezone(tz)
                        timestamps.append(dt)
                        break
                    except Exception:
                        pass
    # Fallback для .log
    if not timestamps and os.path.exists(text_path):
        ts = os.path.getmtime(text_path)
        dt = datetime.fromtimestamp(ts).astimezone(tz)
        timestamps.append(dt)

    # Парсинг .jsonl
    if os.path.exists(json_path) and os.path.getsize(json_path) > 0:
        with open(json_path, "r", encoding="utf-8") as f:
            first_line = f.readline()
            if first_line:
                try:
                    entry = json.loads(first_line)
                    dt = datetime.fromisoformat(entry.get("timestamp"))
                    dt = dt.astimezone(tz)
                    timestamps.append(dt)
                except Exception:
                    pass
    # Fallback для .jsonl
    if not timestamps and os.path.exists(json_path):
        ts = os.path.getmtime(json_path)
        dt = datetime.fromtimestamp(ts).astimezone(tz)
        timestamps.append(dt)

    if timestamps:
        return min(timestamps)
    return None


class PairedZipTimedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, filename, *args, tz: ZoneInfo | None = None, **kwargs):
        super().__init__(filename, *args, **kwargs)
        self.tz = tz
        self.suffix = "%Y-%m-%d_%H-%M-%S%z"  # Кастомный суффикс

    def rotation_filename(self, default_name):
        timestamp = get_earliest_timestamp(os.path.dirname(self.baseFilename), self.tz)
        if timestamp:
            suffix = timestamp.strftime(self.suffix)
        else:
            now = datetime.now(self.tz)
            suffix = now.strftime(self.suffix)
        ext = os.path.splitext(self.baseFilename)[1]  # '.log' или '.jsonl'
        rotated_name = f"{suffix}{ext}"
        return os.path.join(os.path.dirname(self.baseFilename), rotated_name)

    def doRollover(self):
        if not os.path.exists(self.baseFilename) or os.path.getsize(self.baseFilename) == 0:
            return

        try:
            # Вычисляем rotated_name ДО ротации
            self.stream.close()  # Закрываем для чтения
            rotated_name = self.rotation_filename(self.baseFilename)
            rotated_base = os.path.splitext(rotated_name)[0]
            super().doRollover()  # Теперь ротация с известным именем

            # Принудительно ротируем пару, если это .log или .jsonl
            pair_ext = '.jsonl' if self.baseFilename.endswith('.log') else '.log'
            pair_filename = os.path.join(os.path.dirname(self.baseFilename), f'latest{pair_ext}')
            if os.path.exists(pair_filename):
                pair_rotated = f"{rotated_base}{pair_ext}"
                os.rename(pair_filename, pair_rotated)

            # Архивируем
            log_file = f"{rotated_base}.log"
            jsonl_file = f"{rotated_base}.jsonl"
            zip_path = f"{rotated_base}.zip"
            if os.path.exists(log_file) or os.path.exists(jsonl_file):
                with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for f in [log_file, jsonl_file]:
                        if os.path.exists(f):
                            zf.write(f, arcname=os.path.basename(f))
                            os.remove(f)
        except Exception as e:
            logging.error(f"Rollover error: {e}")


class SafeFormatter(logging.Formatter):
    """Formatter that ensures 'log_id' always exists and adds milliseconds."""

    def __init__(self, fmt=None, datefmt=None, tz: ZoneInfo = None):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.tz = tz

    def format(self, record):
        if not hasattr(record, "log_id"):
            record.log_id = str(uuid.uuid4())
        return super().format(record)

    def formatTime(self, record, datefmt=None):
        # создаём datetime с таймзоной
        dt = datetime.fromtimestamp(record.created, tz=self.tz)

        # базовое форматирование (без %f, чтобы не упасть)
        if datefmt:
            if "%f" in datefmt:
                s = dt.strftime(datefmt.replace("%f", "{ms:03d}"))
                s = s.format(ms=dt.microsecond // 1000)
            else:
                s = dt.strftime(datefmt)
        else:
            s = dt.strftime("%Y-%m-%d %H:%M:%S")

        return s


def finalize_previous_logs(base_dir: str, tz: ZoneInfo | None):
    timestamp = get_earliest_timestamp(base_dir, tz)
    if not timestamp:
        return  # Нечего архивировать

    suffix = timestamp.strftime("%Y-%m-%d_%H-%M-%S%z")
    text_path = os.path.join(base_dir, "latest.log")
    json_path = os.path.join(base_dir, "latest.jsonl")
    renamed_log = os.path.join(base_dir, f"{suffix}.log") if os.path.exists(text_path) else None
    renamed_json = os.path.join(base_dir, f"{suffix}.jsonl") if os.path.exists(json_path) else None

    if renamed_log:
        os.rename(text_path, renamed_log)
    if renamed_json:
        os.rename(json_path, renamed_json)

    zip_path = os.path.join(base_dir, f"{suffix}.zip")
    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in [renamed_log, renamed_json]:
                if p and os.path.exists(p):
                    zf.write(p, arcname=os.path.basename(p))
                    os.remove(p)
    except Exception as e:
        logging.error(f"Failed to create ZIP in finalize: {e}")


# === Safe JSON Encoder ===
class SafeJSONEncoder(json.JSONEncoder):
    """
    Universal safe encoder for arbitrary Python objects.
    Converts unknown objects to dict or string.
    """

    def default(self, obj):
        from datetime import datetime, date
        from decimal import Decimal
        import uuid

        # Standard types
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")

        # Try object's __dict__ if available
        if hasattr(obj, "__dict__"):
            try:
                return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
            except Exception:
                return str(obj)

        # Fallback to string representation
        return str(obj)


# === JSON Formatter ===
class JSONFormatter(logging.Formatter):
    """
    Converts log records into structured JSON lines.
    """

    def __init__(self, tz: ZoneInfo | None = None):
        super().__init__()
        self.tz = tz

    def format(self, record):
        if not hasattr(record, "log_id"):
            record.log_id = str(uuid.uuid4())

        dt = datetime.fromtimestamp(record.created)
        if self.tz is None:
            dt = dt.astimezone()
        else:
            dt = dt.astimezone(self.tz)

        log_entry: dict[str, Any] = {
            "id": record.log_id,
            "timestamp": dt.isoformat(timespec='milliseconds'),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Capture all extra fields
        for key, value in record.__dict__.items():
            if key not in log_entry and key not in (
                    "args", "msg", "levelno", "levelname", "exc_info", "exc_text",
                    "stack_info", "lineno", "pathname", "filename", "module",
                    "funcName", "created", "msecs", "relativeCreated", "thread",
                    "threadName", "processName", "process"
            ):
                log_entry[key] = value

        # Include exception details if available
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            log_entry["exception"] = {
                "type": str(exc_type),
                "value": str(exc_value),
                "traceback": traceback.format_exception(exc_type, exc_value, exc_tb),
            }

        return json.dumps(log_entry, cls=SafeJSONEncoder, ensure_ascii=False)


def get_log_level(level_name: str) -> int:
    if not level_name:
        return logging.INFO
    level_name = level_name.upper()
    if level_name == "TRACE":
        return TRACE_LEVEL
    return getattr(logging, level_name, logging.INFO)


# === Logger setup ===
def setup_logger(
        name: str = __name__,
        console_level: str = "INFO",
        file_level: str = "DEBUG",
        json_level: str = "ERROR",
        aiogram_level: str = "INFO",
        timezone: str | None = None,
        backup_limit: int = 0
) -> logging.Logger:
    """
    Initializes a base logger with console, text, and JSON handlers.
    """

    if timezone:
        tz = ZoneInfo(timezone)
    else:
        tz = None

    os.makedirs("storage/logs", exist_ok=True)

    _logger = logging.getLogger(name)
    _logger.setLevel(TRACE_LEVEL)

    if not _logger.handlers:
        text_formatter = SafeFormatter(
            "[%(log_id)s] %(asctime)s - %(levelname)s - %(message)s",
            datefmt="%d.%m.%Y %H:%M:%S.%f%z",
            tz=tz
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(get_log_level(console_level.upper()))
        console_handler.setFormatter(text_formatter)

        finalize_previous_logs("storage/logs", tz)

        # Text file handler
        file_handler = PairedZipTimedRotatingFileHandler(
            "storage/logs/latest.log",
            when="midnight",
            interval=1,
            backupCount=backup_limit,
            encoding="utf-8",
            utc=False,
            tz=tz
        )
        file_handler.setLevel(get_log_level(file_level.upper()))
        file_handler.setFormatter(text_formatter)

        # JSON file handler
        json_handler = PairedZipTimedRotatingFileHandler(
            "storage/logs/latest.jsonl",
            when="midnight",
            interval=1,
            backupCount=backup_limit,
            encoding="utf-8",
            utc=False,
            tz=tz
        )
        json_handler.setLevel(get_log_level(json_level.upper()))
        json_handler.setFormatter(JSONFormatter(tz=tz))

        _logger.addHandler(console_handler)
        _logger.addHandler(file_handler)
        _logger.addHandler(json_handler)

        # --- aiogram logger configuration ---
        aiogram_logger = logging.getLogger("aiogram")
        aiogram_logger.setLevel(get_log_level(aiogram_level.upper()))
        aiogram_logger.addHandler(console_handler)
        aiogram_logger.addHandler(file_handler)
        aiogram_logger.addHandler(json_handler)

    return _logger


# === AppLogger wrapper ===
class AppLogger:
    """
    A wrapper around the standard logger.
    Returns a UUID for each log call and supports *args and **kwargs as extra fields.
    """

    def __init__(self, _logger: logging.Logger):
        self.logger = _logger

    def _log(self, level: int, msg: Any, *args, **kwargs) -> str:
        """
        Core logging method.
        - принимает любые объекты (строки, ошибки и т.п.);
        - автоматически определяет исключения;
        - ВСЕГДА добавляет стек вызовов (для JSON-логов);
        - возвращает UUID лога.
        """
        log_id = str(uuid.uuid4())
        context: dict[str, Any] = {"uuid": log_id}

        detected_exc: BaseException | None = None
        extra_objects: list[Any] = []

        # === 1. Детектируем исключения среди аргументов ===
        for a in args:
            if isinstance(a, BaseException):
                detected_exc = a
            else:
                extra_objects.append(a)

        # === 2. Проверяем исключения в kwargs ===
        for key, value in list(kwargs.items()):
            if isinstance(value, BaseException):
                detected_exc = value
                kwargs.pop(key)

        # === 3. Если msg — ошибка ===
        if isinstance(msg, BaseException):
            detected_exc = msg
            msg = str(msg)

        # === 4. Сохраняем исключение ===
        if detected_exc is not None:
            exc_type = type(detected_exc)
            exc_tb = detected_exc.__traceback__
            context["exception"] = {
                "type": exc_type.__name__,
                "message": str(detected_exc),
                "traceback": traceback.format_exception(exc_type, detected_exc, exc_tb),
            }

        # === 5. Собираем стек вызовов (всегда!) ===
        # Пропускаем первые фреймы (внутри логгера)
        stack = inspect.stack()
        simplified_stack = []
        for frame in stack[2:12]:  # ограничим глубину, чтобы не заливать весь трейс
            simplified_stack.append({
                "file": frame.filename,
                "line": frame.lineno,
                "function": frame.function,
                "code": frame.code_context[0].strip() if frame.code_context else None,
            })
        context["stack"] = simplified_stack

        # === 6. Добавляем args и kwargs ===
        if extra_objects:
            context["args"] = extra_objects
        if kwargs:
            context["kwargs"] = kwargs

        # === 7. Логируем ===
        self.logger.log(
            level,
            str(msg),
            extra={"context": context, "log_id": log_id},
            stacklevel=3  # важно для правильного file/line в record
        )

        return log_id

    # --- Public wrappers ---
    def trace(self, msg: Any, *args, **kwargs) -> str:
        return self._log(TRACE_LEVEL, msg, *args, **kwargs)

    # --- Public wrappers ---
    def debug(self, msg: Any, *args, **kwargs) -> str:
        return self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: Any, *args, **kwargs) -> str:
        return self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: Any, *args, **kwargs) -> str:
        return self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: Any, *args, **kwargs) -> str:
        return self._log(logging.ERROR, msg, *args, **kwargs)

    def _log_query(self, query: str, args: tuple | list = (), level: int = logging.INFO) -> str:
        """
        Private method to log database queries at a given level.
        Combines query and args into a single string.
        Large or binary arguments are masked.
        Datetime objects are converted to ISO format.
        Returns UUID of the log.
        """

        def mask_value(value):
            if isinstance(value, (bytes, bytearray)):
                return f"<bytes {len(value)}B>"
            if isinstance(value, str):
                # Wrap strings in single quotes and escape any internal single quotes
                return "'" + value.replace("'", "''") + "'"
            if isinstance(value, (list, tuple, set)) and len(value) > 10:
                return f"<{type(value).__name__} {len(value)} elements>"
            if isinstance(value, (datetime, date)):
                return f"'{value.isoformat()}'"  # Wrap datetime in quotes for SQL
            if isinstance(value, bool):
                return 'TRUE' if value else 'FALSE'  # SQL boolean syntax
            if value is None:
                return 'NULL'  # SQL NULL
            # Numbers and other types are returned as is
            return value

        masked_args = tuple(mask_value(a) for a in args)

        try:
            log_query = query % masked_args
        except Exception:
            log_query = f"{query} {masked_args}"

        return self._log(level, log_query)

    def trace_db(self, query: str, args: tuple | list = ()) -> str:
        return self._log_query(query, args, level=TRACE_LEVEL)

    def debug_db(self, query: str, args: tuple | list = ()) -> str:
        return self._log_query(query, args, level=logging.DEBUG)

    def info_db(self, query: str, args: tuple | list = ()) -> str:
        return self._log_query(query, args, level=logging.INFO)

    def warning_db(self, query: str, args: tuple | list = ()) -> str:
        return self._log_query(query, args, level=logging.WARNING)

    def error_db(self, query: str, args: tuple | list = ()) -> str:
        return self._log_query(query, args, level=logging.ERROR)


# === Глобальный экземпляр (инициализируется явно после загрузки конфига) ===
logger: AppLogger | None = None


def init_logger(
        console_level: str = "INFO",
        file_level: str = "DEBUG",
        json_level: str = "ERROR",
        aiogram_level: str = "INFO",
        timezone: str | None = None,
        backup_limit: int = 0
) -> AppLogger:
    """
    Инициализировать глобальный логгер с заданными параметрами.

    Должна быть вызвана после загрузки конфигурации в main.py.

    Args:
        console_level: Уровень логирования для консоли
        file_level: Уровень логирования для файла
        json_level: Уровень логирования для JSON
        aiogram_level: Уровень логирования для aiogram
        timezone: Временная зона
        backup_limit: Лимит бэкапов лог-файлов

    Returns:
        Инициализированный AppLogger
    """
    global logger

    _base_logger = setup_logger(
        console_level=console_level,
        file_level=file_level,
        json_level=json_level,
        aiogram_level=aiogram_level,
        timezone=timezone,
        backup_limit=backup_limit
    )
    logger = AppLogger(_base_logger)

    return logger
