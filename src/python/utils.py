import asyncio
import base64
from asyncio import sleep
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Callable, Awaitable

import aiohttp

from python.logger import logger
from python.storage.config import config
from python.storage.strings import get_string

from aiogram import Bot
from aiogram.types import (ChatMember, Message, ReactionTypeEmoji, CallbackQuery, ChatJoinRequest, File,
                           ChatMemberLeft, ChatMemberBanned)


def get_week_number(current_date: datetime) -> int:
    """
    Определяет номер недели (начиная с 1), прошедшей с ближайшей стартовой даты —
    либо 1 февраля, либо 1 сентября — в зависимости от того, какая из них последняя до текущей даты.

    Недели считаются с понедельника по субботу. Если стартовая дата выпадает на воскресенье,
    то неделя начинается с понедельника следующего дня. Воскресенье всегда относится к предыдущей неделе.

    Параметры:
    current_date (datetime): Текущая дата, для которой нужно вычислить номер недели.

    Возвращает:
    int: Номер недели, начиная с ближайшей стартовой даты. Если до стартовой даты — возвращает 0.
    """
    # Стартовые даты (мес, день)
    ref_month_day_1 = (2, 1)  # 1 февраля
    ref_month_day_2 = (9, 1)  # 1 сентября

    year = current_date.year
    start_feb = datetime(year, *ref_month_day_1)
    start_sep = datetime(year, *ref_month_day_2)

    # Выбираем ближайшую прошедшую стартовую дату
    if current_date >= start_sep:
        start_date = start_sep
    elif current_date >= start_feb:
        start_date = start_feb
    else:
        # Ещё до 1 февраля текущего года — берём 1 сентября прошлого года
        start_date = datetime(year - 1, *ref_month_day_2)

    # Если стартовая дата — воскресенье, сдвигаем на следующий понедельник
    if start_date.weekday() == 6:  # 6 == Sunday
        start_date += timedelta(days=1)

    # Если current_date — воскресенье, считаем его частью предыдущей (субботней) недели
    calc_date = current_date
    if calc_date.weekday() == 6:  # если Sunday
        calc_date -= timedelta(days=1)

    # Ещё до старта — 0
    if calc_date < start_date:
        return 0

    # Нумеруем недели: первая неделя = 1, и +1 при каждом новом понедельнике
    week = 1
    days_between = (calc_date - start_date).days
    for i in range(1, days_between + 1):
        if (start_date + timedelta(days=i)).weekday() == 0:  # 0 == Monday
            week += 1

    return week


async def is_user_in_chat(bot: Bot, chat_id: int | str, user_id: int) -> bool:
    """
    Проверяет, состоит ли пользователь в чате.

    :param bot: Экземпляр aiogram.Bot
    :param chat_id: ID чата или @username
    :param user_id: ID пользователя
    :return: True, если пользователь в чате, иначе False
    """
    try:
        member: ChatMember = await bot.get_chat_member(chat_id, user_id)
        return not isinstance(member, (ChatMemberLeft, ChatMemberBanned))
    except Exception:
        # Например, если бот не состоит в чате или нет прав на просмотр
        return False


async def await_and_run(delay_time: float, task) -> None:
    await asyncio.sleep(delay_time)
    await task()


@dataclass
class TimeDelta:
    days: int
    hours: int
    minutes: int
    seconds: int = 0
    microseconds: int = 0
    is_positive: bool = True

    @staticmethod
    def create_from_delta(delta: timedelta, is_positive=True) -> "TimeDelta":
        total_seconds = int(delta.total_seconds())
        days, rem = divmod(total_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)
        return TimeDelta(days, hours, minutes, seconds, delta.microseconds, is_positive)

    def round(self) -> "TimeDelta":
        if self.microseconds > 0 and self.seconds != 0:
            self.microseconds = 0
            self.seconds += 1
        if self.seconds > 0 and self.minutes != 0:
            self.seconds = 0
            self.minutes += 1
        if self.minutes > 30 and self.hours != 0:
            self.minutes = 0
            self.hours += 1
        if self.hours > 0 and self.days != 0:
            self.hours = 0
            self.days += 1
        return self

    @property
    def total_days(self) -> float:
        return (
                self.days
                + self.hours / 24
                + self.minutes / (24 * 60)
                + self.seconds / 86400
                + self.microseconds / 86_400_000_000
        )

    @property
    def total_hours(self) -> float:
        return (
                self.days * 24
                + self.hours
                + self.minutes / 60
                + self.seconds / 3600
                + self.microseconds / 3_600_000_000
        )

    @property
    def total_minutes(self) -> float:
        return (
                self.days * 1440
                + self.hours * 60
                + self.minutes
                + self.seconds / 60
                + self.microseconds / 60_000_000
        )

    @property
    def total_seconds(self) -> float:
        return (
                self.days * 86400
                + self.hours * 3600
                + self.minutes * 60
                + self.seconds
                + self.microseconds / 1_000_000
        )

    @property
    def total_microseconds(self) -> float:
        return (
                self.days * 86_400_000_000
                + self.hours * 3_600_000_000
                + self.minutes * 60_000_000
                + self.seconds * 1_000_000
                + self.microseconds
        )

    def parse_string(self, lang: str) -> str:
        if self.is_positive:
            if self.days > 2:
                return get_string(lang, "time.format.future.d", self.days)
            elif self.days == 2:
                return get_string(lang, "time.format.future.2d")
            elif self.days == 1:
                return get_string(lang, "time.format.future.1d")
            elif self.hours > 0:
                return get_string(lang, "time.format.future.h", self.hours)
            elif self.minutes > 0:
                return get_string(lang, "time.format.future.m", self.minutes)
            elif self.seconds > 0:
                return get_string(lang, "time.format.future.s", self.seconds)
            elif self.microseconds > 0:
                return get_string(lang, "time.format.future.u", self.microseconds)
            else:
                return get_string(
                    lang,
                    "time.format.future.unknown",
                    d=self.days, h=self.hours, m=self.minutes, s=self.seconds, u=self.microseconds,
                )
        else:
            if self.days > 2:
                return get_string(lang, "time.format.past.d", self.days)
            elif self.days == 2:
                return get_string(lang, "time.format.past.2d")
            elif self.days == 1:
                return get_string(lang, "time.format.past.1d")
            elif self.hours > 0:
                return get_string(lang, "time.format.past.h", self.hours)
            elif self.minutes > 0:
                return get_string(lang, "time.format.past.m", self.minutes)
            elif self.seconds > 0:
                return get_string(lang, "time.format.past.s", self.seconds)
            elif self.microseconds > 0:
                return get_string(lang, "time.format.past.u", self.microseconds)
            else:
                return get_string(
                    lang,
                    "time.format.past.unknown",
                    d=self.days, h=self.hours, m=self.minutes, s=self.seconds, u=self.microseconds,
                )


async def check_blacklisted(message: Message) -> bool:
    for chat in config.blacklisted:
        if message.chat.id == chat.chat_id:
            if chat.topics:
                for topic in chat.topics:
                    if topic == message.message_thread_id:
                        await message.react([ReactionTypeEmoji(emoji="👎")])
                        await sleep(3)
                        await message.delete()
                        return True
                return False
            await message.react([ReactionTypeEmoji(emoji="👎")])
            await sleep(3)
            await message.delete()
            return True
    return False


async def log_exception(e: Exception, original: Message | CallbackQuery | ChatJoinRequest) -> None:
    code = logger.error(e, original)
    await original.reply(
        get_string(
            original.from_user.language_code,
            "exceptions.uncause",
            code,
            config.chat_config.owner
        )
    )
    await original.bot.send_message(
        config.chat_config.admin.chat_id,
        get_string(
            config.chat_config.admin.chat_lang,
            "exceptions.debug",
            code=code, exc=str(e),
            userid=original.from_user.id,
            username=original.from_user.username,
            fullname=original.from_user.full_name,
        ),
        message_thread_id=config.chat_config.admin.topics.debug
    )


async def download_photos(
        bot: Bot,
        file_ids: List[str],
        progress_callback: Optional[Callable[[int, int], Awaitable[None]]] = None
) -> List[str]:
    """
    Скачивает все фото или видео из списка file_ids через nginx и возвращает список Base64-строк.
    """
    base64_photos = []
    await progress_callback(0, len(file_ids))
    async with aiohttp.ClientSession() as session:
        for i, file_id in enumerate(file_ids):
            try:
                # Получаем информацию о файле через nginx
                file: File = await bot.get_file(file_id)

                # Обрезаем префикс /var/lib/telegram-bot-api/
                relative_path = file.file_path.lstrip('/var/lib/telegram-bot-api/')

                # Формируем URL для скачивания
                download_url = f"{config.telegram.download_server}/file/{relative_path}"

                # Скачиваем файл
                async with session.get(download_url) as response:
                    if response.status != 200:
                        raise Exception(f"Ошибка скачивания: {response.status}, URL: {download_url}")
                    file_bytes = await response.read()

                # Преобразуем в Base64
                photo_b64 = base64.b64encode(file_bytes).decode('utf-8')
                base64_photos.append(photo_b64)

            except Exception as e:
                logger.error(f"Ошибка при скачивании file_id={file_id}: {str(e)}")
                continue  # Пропускаем ошибочный файл

            await progress_callback(i + 1, len(file_ids))
    return base64_photos


async def download_video(
        bot: Bot,
        file_id: str | None,
        progress_callback: Optional[Callable[[int], Awaitable[None]]] = None
) -> str | None:
    """
    Downloads a video through nginx (local Telegram Bot API) and returns Base64 encoded data.
    Calls the progress_callback with the download percentage (only on change).

    Args:
        bot: Telegram Bot API Instance
        file_id: The Telegram file ID to download.
        progress_callback: Optional callback function to report download progress (percentage).

    Returns:
        Base64 encoded string of the video or None if file_id is invalid.
    """
    if not file_id:
        return None

    # Get file information
    file_info: File = await bot.get_file(file_id)

    # file_path: /var/lib/telegram-bot-api/<token>/videos/file_0.mp4
    # Strip prefix to get relative path: <token>/videos/file_0.mp4
    relative_path = file_info.file_path.lstrip('/var/lib/telegram-bot-api/')

    # Form the download URL for nginx
    download_url = f"{config.telegram.download_server}/file/{relative_path}"

    # Download file with progress tracking
    async with aiohttp.ClientSession() as session:
        async with session.get(download_url) as response:
            if response.status != 200:
                raise Exception(f"Download error: {response.status}, URL: {download_url}")

            # Get total size of the file (if available)
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            last_reported_percentage = -1  # Track last reported percentage to avoid duplicates
            data_bytes = bytearray()

            # Read response in chunks to track progress
            chunk_size = 1024 * 1024  # 1MB chunks
            async for chunk in response.content.iter_chunked(chunk_size):
                data_bytes.extend(chunk)
                downloaded += len(chunk)

                # Calculate and report progress if total_size is known
                if total_size > 0 and progress_callback:
                    percentage = int((downloaded / total_size) * 100)
                    if percentage != last_reported_percentage:
                        last_reported_percentage = percentage
                        await progress_callback(percentage)

    # Encode to Base64
    return base64.b64encode(data_bytes).decode("utf-8")
