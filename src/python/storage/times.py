from dataclasses import dataclass
from datetime import time, timedelta, datetime
from enum import Enum
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


class TimeStatus(Enum):
    OPEN = "open"  # Сейчас открыто
    REMAIN = "remain"  # До открытия
    PASSED = "passed"  # Уже закрылось


@dataclass(frozen=True)
class TimeDeltaInfo:
    status: TimeStatus
    delta: timedelta  # сколько времени до/после (для OPEN – до закрытия)


def get_time(time_address: str) -> TimeDeltaInfo | None:
    parts = time_address.split(".")
    node = times
    for p in parts:
        node = node[p]

    if not isinstance(node, list):
        return None

    tz = ZoneInfo(config.timezone)
    now = datetime.now(tz)

    deltas: list[TimeDeltaInfo] = []

    for shift in range(0, 8):  # только сегодня и вперёд
        day = now.date() + timedelta(days=shift)
        weekday = day.weekday()

        for entry in node:
            if weekday in entry.days:
                for t in entry.times:
                    start_dt = datetime.combine(day, t.start, tz)
                    end_dt = datetime.combine(day, t.end, tz)

                    # обработка перехода на следующий день
                    if end_dt <= start_dt:
                        end_dt += timedelta(days=1)

                    if start_dt <= now <= end_dt and shift == 0:
                        return TimeDeltaInfo(TimeStatus.OPEN, end_dt - now)

                    if shift == 0:
                        if now < start_dt:
                            deltas.append(TimeDeltaInfo(TimeStatus.REMAIN, start_dt - now))
                        elif now > end_dt:
                            deltas.append(TimeDeltaInfo(TimeStatus.PASSED, now - end_dt))
                    else:
                        if now < start_dt:
                            deltas.append(TimeDeltaInfo(TimeStatus.REMAIN, start_dt - now))

    if not deltas:
        return None

    # ближайший по времени (по абсолютному значению)
    return min(deltas, key=lambda d: d.delta.total_seconds())


def get_time_status(time_address: str) -> str | None:
    info = get_time(time_address)
    if info is None:
        return None

    total_seconds = int(info.delta.total_seconds())
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    micros = info.delta.microseconds

    if micros > 0 and seconds != 0:
        seconds += 1
    if seconds > 0 and minutes != 0:
        minutes += 1
    if hours > 0 and days != 0:
        days += 1
    if minutes > 30 and hours != 0:
        hours += 1

    if info.status == TimeStatus.OPEN:
        if days > 0:
            return get_string("time.open.d", days)
        elif hours > 0:
            return get_string("time.open.h", hours)
        elif minutes > 0:
            return get_string("time.open.m", minutes)
        else:
            return get_string("time.open.s", seconds)

    if info.status == TimeStatus.REMAIN:
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

    if info.status == TimeStatus.PASSED:
        if hours > 0:
            return get_string("time.passed.h", hours)
        elif minutes > 0:
            return get_string("time.passed.m", minutes)
        else:
            return get_string("time.passed.s", seconds)

    return None
