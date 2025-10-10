import json
import logging
import os
import traceback
import uuid
from datetime import datetime, timezone, date
from typing import Any


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


# === Logger setup ===
def setup_logger(name: str = __name__,
                 console_level: str = "INFO",
                 file_level: str = "DEBUG",
                 json_level: str = "ERROR") -> logging.Logger:
    """
    Initializes a base logger with console, text, and JSON handlers.
    """
    os.makedirs("storage/logs", exist_ok=True)
    log_filename = f"storage/logs/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    json_log_filename = f"storage/logs/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_structured.json"

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        text_formatter = logging.Formatter(
            "[%(log_id)s] %(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
        console_handler.setFormatter(text_formatter)

        # Text file handler
        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        file_handler.setLevel(getattr(logging, file_level.upper(), logging.DEBUG))
        file_handler.setFormatter(text_formatter)

        # JSON file handler
        json_handler = logging.FileHandler(json_log_filename, encoding="utf-8")
        json_handler.setLevel(getattr(logging, json_level.upper(), logging.ERROR))
        json_handler.setFormatter(JSONFormatter())

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.addHandler(json_handler)

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
        Core logging function.
        Accepts arbitrary data, detects Exception automatically.
        """
        log_id = str(uuid.uuid4())

        # Core context container
        context: dict[str, Any] = {"uuid": log_id}

        # Detect Exception objects among args/kwargs
        detected_exc = None

        # Scan *args for exceptions
        clean_args = []
        for a in args:
            if isinstance(a, BaseException):
                detected_exc = a
            else:
                clean_args.append(a)

        # Scan kwargs for exceptions
        for k, v in list(kwargs.items()):
            if isinstance(v, BaseException):
                detected_exc = v
                kwargs.pop(k)

        # If message itself is an exception
        if isinstance(msg, BaseException):
            detected_exc = msg
            msg = str(msg)

        # Extract traceback if exception detected
        if detected_exc is not None:
            exc_type = type(detected_exc)
            exc_value = detected_exc
            exc_tb = detected_exc.__traceback__
            tb_formatted = traceback.format_exception(exc_type, exc_value, exc_tb)

            context["exception"] = {
                "type": exc_type.__name__,
                "message": str(exc_value),
                "traceback": tb_formatted,
            }

        # Merge args/kwargs into context
        if clean_args:
            context["args"] = clean_args
        if kwargs:
            context["kwargs"] = kwargs

        # Log the record
        self._logger.log(level, str(msg), extra={"context": context})
        return log_id

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
            if isinstance(value, str) and len(value) > 50:
                return f"<str {len(value)} chars>"
            if isinstance(value, (list, tuple, set)) and len(value) > 10:
                return f"<{type(value).__name__} {len(value)} elements>"
            if isinstance(value, (datetime, date)):
                return value.isoformat()
            # fallback for other objects
            return value

        masked_args = tuple(mask_value(a) for a in args)

        try:
            log_query = query % masked_args
        except Exception:
            log_query = f"{query} {masked_args}"

        return self._log(level, log_query)

    def debug_db(self, query: str, args: tuple = ()) -> str:
        return self._log_query(query, args, level=logging.DEBUG)

    def info_db(self, query: str, args: tuple = ()) -> str:
        return self._log_query(query, args, level=logging.INFO)

    def warning_db(self, query: str, args: tuple = ()) -> str:
        return self._log_query(query, args, level=logging.WARNING)

    def error_db(self, query: str, args: tuple = ()) -> str:
        return self._log_query(query, args, level=logging.ERROR)


# === Global logger instance ===
_base_logger = setup_logger()
logger = AppLogger(_base_logger)
