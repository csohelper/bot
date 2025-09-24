from dataclasses import dataclass
from datetime import time, timedelta, datetime
from zoneinfo import ZoneInfo

import yaml

from python.storage.config import config
from python.storage.strings import get_string


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


with open("src/res/times.yaml", "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

times = walk(data)


def get_time(time_address: str) -> timedelta | None:
    parts = time_address.split(".")
    node = times
    for p in parts:
        node = node[p]

    if not isinstance(node, list):
        return None

    tz = ZoneInfo(config.timezone)
    now = datetime.now(tz)

    deltas: list[timedelta] = []

    # Проверяем сегодня и до недели вперёд
    for shift in range(0, 8):  # только будущее (включая сегодня)
        day = now.date() + timedelta(days=shift)
        weekday = day.weekday()

        for entry in node:
            if weekday in entry.days:
                for t in entry.times:
                    start_dt = datetime.combine(day, t.start, tz)
                    end_dt = datetime.combine(day, t.end, tz)

                    if start_dt <= now <= end_dt and shift == 0:
                        return timedelta(0)  # прямо сейчас открыто

                    if shift == 0:
                        if now < start_dt:
                            # сегодня ещё не началось → приоритет
                            deltas.append(start_dt - now)
                        elif now > end_dt:
                            # сегодня уже закрылось → приоритет
                            deltas.append(-(now - end_dt))
                    else:
                        # будущее дни → только положительные интервалы
                        if now < start_dt:
                            deltas.append(start_dt - now)

    if not deltas:
        return None

    # выбираем ближайший по абсолютному времени
    return min(deltas, key=lambda d: abs(d.total_seconds()))


def get_time_status(time_address: str) -> str | None:
    delta = get_time(time_address)
    if delta is None:
        return None

    total_seconds = int(delta.total_seconds())

    if total_seconds == 0:
        return get_string("time.open")

    if total_seconds > 0:  # ещё не открылось
        days, rem = divmod(total_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)

        if days >= 3:
            return get_string("time.remain.d", days)
        elif days == 2:
            return get_string("time.remain.2d")
        elif days == 1:
            return get_string("time.remain.1d")
        elif hours > 0:
            return get_string("time.remain.h", hours)
        elif minutes > 0:
            return get_string("time.remain.m", minutes)
        else:
            return get_string("time.remain.s", seconds)

    else:  # уже закрылось
        total_seconds = abs(total_seconds)
        hours, rem = divmod(total_seconds, 3600)
        minutes, seconds = divmod(rem, 60)

        if hours > 0:
            return get_string("time.passed.h", hours)
        elif minutes > 0:
            return get_string("time.passed.m", minutes)
        else:
            return get_string("time.passed.s", seconds)
