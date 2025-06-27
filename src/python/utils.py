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
    ref_month_day_1 = (2, 1)   # 1 февраля
    ref_month_day_2 = (9, 1)   # 1 сентября

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

# if __name__ == "__main__":
#     tests = [
#         (datetime(2024, 2, 29), 5),
#         (datetime(2024, 4, 8),  11),
#         (datetime(2025, 3, 29), 9),
#         (datetime(2025, 4, 22), 13),
#         (datetime(2025, 4, 29), 14),
#         (datetime(2025, 5, 4),  14),
#         (datetime(2025, 6, 17), 21),
#         (datetime(2025, 6, 28), 22),
#     ]

#     for date, expected in tests:
#         result = get_week_number(date)
#         print(f"{date.date():<10} → got {result}, expected {expected}")

# print(get_week_number(datetime(2024, 2, 29)), "should be 5; четверг, 29 февраля 2024 года")
# print(get_week_number(datetime(2024, 4, 8)), "should be 11; понедельник, 8 апреля 2024 года")
# print(get_week_number(datetime(2025, 3, 29)), "should be 9; суббота, 29 марта 2025 года")
# print(get_week_number(datetime(2025, 4, 22)), "should be 13; вторник, 22 апреля 2025 года")
# print(get_week_number(datetime(2025, 4, 29)), "should be 14; вторник, 29 апреля 2025 года")
# print(get_week_number(datetime(2025, 5, 4)), "should be 14; воскресенье, 4 мая 2025 года")
# print(get_week_number(datetime(2025, 6, 17)), "should be 21; вторник, 17 июня 2025 года")
# print(get_week_number(datetime(2025, 6, 28)), "should be 22; суббота, 28 июня 2025 года")
# print(get_week_number(datetime.now()))