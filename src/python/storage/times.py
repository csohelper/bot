from dataclasses import dataclass
from datetime import time, timedelta, datetime
from enum import Enum
from zoneinfo import ZoneInfo

import yaml

from python.storage import config as config_module
from python.storage.strings import get_string
from python.utils import TimeDelta


@dataclass(frozen=True)
class Time:
    start: time
    end: time


@dataclass(frozen=True)
class Times:
    days: list[int]
    times: list[Time]


def parse_time_string(s) -> time:
    if isinstance(s, time):
        return s

    if isinstance(s, int):
        # трактуем как минуты от полуночи
        h, m = divmod(s, 60)
        return time(h, m)

    if isinstance(s, float):
        # трактуем как секунды от полуночи (с дробной частью)
        total_seconds = s
        h, rem = divmod(int(total_seconds), 3600)
        m, sec = divmod(rem, 60)
        micro = int((total_seconds - int(total_seconds)) * 1_000_000)
        return time(h, m, sec, micro)

    if isinstance(s, str):
        parts = s.split(":")
        if len(parts) < 2:
            raise ValueError(f"Invalid time string: {s}")

        h = int(parts[0])
        m = int(parts[1])
        sec = 0
        micro = 0

        if len(parts) >= 3:
            if "." in parts[2]:  # секунды и микросекунды
                sec_part, micro_part = parts[2].split(".")
                sec = int(sec_part)
                micro = int((micro_part + "000000")[:6])
            else:
                sec = int(parts[2])

        return time(h, m, sec, micro)

    raise ValueError(f"Unsupported type for time: {type(s)} ({s})")


def parse_times_entry(entry: dict) -> Times:
    return Times(
        days=entry["days"],
        times=[Time(parse_time_string(t["start"]), parse_time_string(t["end"]))
               for t in entry["times"]]
    )


def walk(node):
    """Рекурсивно обходит YAML-узел и возвращает вложенную структуру."""
    if isinstance(node, list):
        # список расписаний
        return [parse_times_entry(item) for item in node]

    elif isinstance(node, dict):
        return {key: walk(value) for key, value in node.items()}

    else:
        raise ValueError(f"Unexpected node type: {type(node)}")


with open("src/res/strings/times.yaml", "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

times = walk(data)


class TimeStatus(Enum):
    OPEN = "open"  # Сейчас открыто
    CLOSED = "remain"  # Сейчас закрыто


@dataclass(frozen=True)
class TimeDeltaInfo:
    status: TimeStatus
    delta_past: timedelta  # сколько времени прошло с открытия / закрытия
    delta_future: timedelta  # сколько времени осталось до закрытия / открытия


def get_time(time_address: str) -> TimeDeltaInfo | None:
    parts = time_address.split(".")
    node = times
    for p in parts:
        node = node[p]

    if not isinstance(node, list):
        return None

    if config_module.config.timezone:
        tz = ZoneInfo(config_module.config.timezone)
    else:
        tz = None
    now = datetime.now(tz)

    past_candidates: list[tuple[datetime, datetime]] = []
    future_candidates: list[tuple[datetime, datetime]] = []

    # смотрим неделю назад и неделю вперёд
    for shift in range(-7, 8):
        day = now.date() + timedelta(days=shift)
        weekday = day.weekday()

        for entry in node:
            if weekday in entry.days:
                for t in entry.times:
                    start_dt = datetime.combine(day, t.start, tz)
                    end_dt = datetime.combine(day, t.end, tz)

                    # корректировка, если "перелив" на следующий день
                    if end_dt <= start_dt:
                        end_dt += timedelta(days=1)

                    if end_dt <= now:
                        # уже полностью прошло
                        past_candidates.append((start_dt, end_dt))
                    elif start_dt > now:
                        # ещё не началось
                        future_candidates.append((start_dt, end_dt))
                    else:
                        # сейчас открыто
                        return TimeDeltaInfo(
                            status=TimeStatus.OPEN,
                            delta_past=now - start_dt,
                            delta_future=end_dt - now,
                        )

    # если закрыто, ищем ближайшую пару "прошлый слот -> следующий слот"
    if past_candidates and future_candidates:
        last_past = max(past_candidates, key=lambda x: x[1])  # ближайшее прошедшее закрытие
        next_future = min(future_candidates, key=lambda x: x[0])  # ближайшее будущее открытие
        return TimeDeltaInfo(
            status=TimeStatus.CLOSED,
            delta_past=now - last_past[1],  # прошло с момента закрытия
            delta_future=next_future[0] - now,  # осталось до открытия
        )

    return None


def get_time_status(time_address: str, lang: str) -> str | None:
    info = get_time(time_address)
    if info is None:
        return None

    future = TimeDelta.create_from_delta(info.delta_future).round()
    past = TimeDelta.create_from_delta(info.delta_past, False).round()

    if info.status == TimeStatus.CLOSED:
        if future.total_hours < 1:
            status = get_string(lang, "time.colors.opening")
        else:
            status = get_string(lang, "time.colors.closed")
        if past.total_hours < 8:
            key = "time.placeholders.early_closed"
        else:
            key = "time.placeholders.closed"
        return get_string(
            lang,
            key,
            status=status,
            closed_time=past.parse_string(lang),
            opening_time=future.parse_string(lang)
        )
    elif info.status == TimeStatus.OPEN:
        if future.total_hours < 1:
            status = get_string(lang, "time.colors.closing")
        else:
            status = get_string(lang, "time.colors.open")
        if past.total_hours < 1:
            key = "time.placeholders.early_open"
        else:
            key = "time.placeholders.open"

        return get_string(
            lang,
            key,
            status=status,
            opened_time=past.parse_string(lang),
            closing_time=future.parse_string(lang)
        )
    else:
        return None
