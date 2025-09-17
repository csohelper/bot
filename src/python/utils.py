import asyncio
from datetime import datetime, timedelta


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


from aiogram import Bot
from aiogram.types import ChatMember


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
        return member.status not in ("left", "kicked")
    except Exception:
        # Например, если бот не состоит в чате или нет прав на просмотр
        return False


async def await_and_run(delay_time: float, task) -> None:
    await asyncio.sleep(delay_time)
    await task()
