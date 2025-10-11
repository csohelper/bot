import json
import logging
import os
import traceback
import uuid
from datetime import datetime, timezone, date
from typing import Any

from python.storage.config import config

TRACE_LEVEL = 5  # ниже DEBUG (10)
logging.addLevelName(TRACE_LEVEL, "TRACE")


class SafeFormatter(logging.Formatter):
    """Formatter that ensures 'log_id' always exists."""

    def format(self, record):
        if not hasattr(record, "log_id"):
            record.log_id = str(uuid.uuid4())
        return super().format(record)


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

    def format(self, record):
        if not hasattr(record, "log_id"):
            record.log_id = str(uuid.uuid4())

        log_entry: dict[str, Any] = {
            "id": record.log_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
        aiogram_level: str = "INFO"
) -> logging.Logger:
    """
    Initializes a base logger with console, text, and JSON handlers.
    """
    os.makedirs("storage/logs/json", exist_ok=True)
    log_filename = f"storage/logs/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    json_log_filename = f"storage/logs/json/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"

    logger = logging.getLogger(name)
    logger.setLevel(TRACE_LEVEL)

    if not logger.handlers:
        text_formatter = SafeFormatter(
            "[%(log_id)s] %(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(get_log_level(console_level.upper()))
        console_handler.setFormatter(text_formatter)

        # Text file handler
        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        file_handler.setLevel(get_log_level(file_level.upper()))
        file_handler.setFormatter(text_formatter)

        # JSON file handler
        json_handler = logging.FileHandler(json_log_filename, encoding="utf-8")
        json_handler.setLevel(get_log_level(json_level.upper()))
        json_handler.setFormatter(JSONFormatter())

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.addHandler(json_handler)

        # --- aiogram logger configuration ---
        aiogram_logger = logging.getLogger("aiogram")
        aiogram_logger.setLevel(get_log_level(aiogram_level.upper()))
        aiogram_logger.addHandler(console_handler)
        aiogram_logger.addHandler(file_handler)
        aiogram_logger.addHandler(json_handler)

    return logger


# === AppLogger wrapper ===
class AppLogger:
    """
    A wrapper around the standard logger.
    Returns a UUID for each log call and supports *args and **kwargs as extra fields.
    """

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _log(self, level: int, msg: Any, *args, **kwargs) -> str:
        """
        Core logging method.
        Accepts any objects in msg, *args, and **kwargs.
        Detects exceptions automatically, even if multiple arguments are provided.
        """
        log_id = str(uuid.uuid4())
        context: dict[str, Any] = {"uuid": log_id}

        detected_exc: BaseException | None = None
        extra_objects: list[Any] = []

        # Detect exceptions among args
        for a in args:
            if isinstance(a, BaseException):
                detected_exc = a
            else:
                extra_objects.append(a)

        # Detect exceptions in kwargs (rare but allowed)
        for key, value in list(kwargs.items()):
            if isinstance(value, BaseException):
                detected_exc = value
                kwargs.pop(key)

        # Detect exception if msg itself is one
        if isinstance(msg, BaseException):
            detected_exc = msg
            msg = str(msg)

        # Build exception block if found
        if detected_exc is not None:
            exc_type = type(detected_exc)
            exc_tb = detected_exc.__traceback__
            context["exception"] = {
                "type": exc_type.__name__,
                "message": str(detected_exc),
                "traceback": traceback.format_exception(exc_type, detected_exc, exc_tb),
            }

        # Include remaining args and kwargs
        if extra_objects:
            context["args"] = extra_objects
        if kwargs:
            context["kwargs"] = kwargs

        # Log the message
        self._logger.log(level, str(msg), extra={
            "context": context,
            "log_id": log_id
        })
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

    def _log_query(self, query: str, args: tuple = (), level: int = logging.INFO) -> str:
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

    def trace_db(self, query: str, args: tuple = ()) -> str:
        return self._log_query(query, args, level=TRACE_LEVEL)

    def debug_db(self, query: str, args: tuple = ()) -> str:
        return self._log_query(query, args, level=logging.DEBUG)

    def info_db(self, query: str, args: tuple = ()) -> str:
        return self._log_query(query, args, level=logging.INFO)

    def warning_db(self, query: str, args: tuple = ()) -> str:
        return self._log_query(query, args, level=logging.WARNING)

    def error_db(self, query: str, args: tuple = ()) -> str:
        return self._log_query(query, args, level=logging.ERROR)


# === Global logger instance ===
_base_logger = setup_logger(
    console_level=config.logger.console_level,
    file_level=config.logger.file_level,
    json_level=config.logger.json_level,
    aiogram_level=config.logger.aiogram_level
)
logger = AppLogger(_base_logger)
