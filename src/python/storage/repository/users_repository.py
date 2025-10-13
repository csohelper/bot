import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, FrozenSet

from python.logger import logger
from python.storage import database


@dataclass(frozen=True)
class Resident:
    id: int
    user_id: int
    username: str
    fullname: str
    name: str
    surname: str
    room: Optional[int]
    status: str
    processed_by: Optional[int]
    processed_by_fullname: Optional[str]
    processed_by_username: Optional[str]
    refuse_reason: Optional[str]
    created_at: datetime
    image: Optional[str]
    lang: Optional[str]


async def init_database_module() -> None:
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL UNIQUE,
                    username TEXT NOT NULL,
                    fullname TEXT NOT NULL,
                    lang TEXT
                )
            """
            logger.trace_db(query)
            await cur.execute(query)
            query = """
                CREATE TABLE IF NOT EXISTS residents (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL UNIQUE,
                    username TEXT,
                    fullname TEXT NOT NULL,
                    name TEXT NOT NULL,
                    surname TEXT NOT NULL,
                    room INTEGER,
                    image TEXT,
                    status TEXT DEFAULT 'moderation',
                    processed_by BIGINT,
                    processed_by_fullname TEXT,
                    processed_by_username TEXT,
                    refuse_reason TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    lang TEXT
                )
            """
            logger.trace_db(query)
            await cur.execute(query)
            query = """
                CREATE TABLE IF NOT EXISTS requests (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL UNIQUE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN NOT NULL DEFAULT FALSE,
                    greeting_msg INTEGER,
                    lang TEXT
                )
            """
            logger.trace_db(query)
            await cur.execute(query)
            await conn.commit()


@dataclass(frozen=True, slots=True)
class UserRecord:
    user_id: int
    username: Optional[str]
    fullname: str
    lang: Optional[str]


async def check_user(user: UserRecord):
    async def _task():
        async with database.get_db_connection() as conn:
            async with conn.cursor() as cur:
                query = """
                        INSERT INTO users (user_id, username, fullname, lang)
                        VALUES (%s, %s, %s, %s) ON CONFLICT (user_id) DO
                        UPDATE
                            SET username = EXCLUDED.username,
                            fullname = EXCLUDED.fullname,
                            lang = EXCLUDED.lang \
                        """
                values = (user.user_id, user.username, user.fullname, user.lang)
                logger.trace_db(query, values)
                await cur.execute(
                    query,
                    values
                )
                await conn.commit()

    # Запускаем без await — фоново
    asyncio.create_task(_task())


async def add_resident(
        user_id: int,
        username: str | None,
        fullname: str,
        name: str,
        surname: str,
        room: int | None = None,
        image: str | None = None,
        status: str = "waiting",
        lang: str | None = None,
) -> int:
    """
    Добавляет пользователя в таблицу residents или обновляет его данные.
    Возвращает id (PRIMARY KEY) из таблицы residents.

    :param user_id: Telegram user_id
    :param username: username (без @)
    :param fullname: Полное имя из Telegram
    :param name: Имя (из анкеты)
    :param surname: Фамилия (из анкеты)
    :param room: Комната (может быть None)
    :param status: Статус (по умолчанию 'waiting')
    :param image: Изображение подтверждения в base64 (JPG)
    :param lang: Код языка пользователя
    :return: id записи в таблице residents
    """
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = """
                    INSERT INTO residents (user_id, username, fullname, name, surname, room, status, image, lang)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id \
                    """
            values = (user_id, username, fullname, name, surname, room, status, image, lang)
            logger.trace_db(query, values)
            await cur.execute(query, values)
            row = await cur.fetchone()
            await conn.commit()
            return row[0]


async def get_resident_by_id(user_id: int) -> Resident | None:
    """
    Возвращает пользователя из таблицы users по его id (PRIMARY KEY).

    :param user_id: id из таблицы users (не Telegram user_id!)
    :return: User или None, если не найден
    """
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = """
                    SELECT id,
                           user_id,
                           username,
                           fullname,
                           name,
                           surname,
                           room,
                           status,
                           processed_by,
                           processed_by_fullname,
                           processed_by_username,
                           refuse_reason,
                           created_at,
                           image,
                           lang
                    FROM residents
                    WHERE id = %s \
                    """
            values = (user_id,)
            logger.trace_db(query, values)
            logger.debug(values)
            await cur.execute(
                query,
                values
            )
            row = await cur.fetchone()

            if not row:
                return None

            return Resident(
                id=row[0],
                user_id=row[1],
                username=row[2],
                fullname=row[3],
                name=row[4],
                surname=row[5],
                room=row[6],
                status=row[7],
                processed_by=row[8],
                processed_by_fullname=row[9],
                processed_by_username=row[10],
                refuse_reason=row[11],
                created_at=row[12],
                image=row[13],
                lang=row[14]
            )


ALLOWED_USER_FIELDS = {
    "username", "fullname", "name", "surname", "room", "status",
    "processed_by", "processed_by_fullname", "processed_by_username",
    "refuse_reason", "image", "lang"
}


async def update_resident_fields(resident_id: int, **fields) -> Optional[Resident]:
    """
    Обновляет указанные поля пользователя в таблице users.
    Возвращает объект User после обновления или None, если запись не найдена
    """
    # Оставляем только разрешённые поля
    updates = {k: v for k, v in fields.items() if k in ALLOWED_USER_FIELDS}
    if not updates:
        return None

    # Формируем SET часть SQL
    set_clause = ", ".join([f"{key} = %s" for key in updates.keys()])
    values = list(updates.values())
    values.append(resident_id)

    query = f"""
        UPDATE residents
        SET {set_clause}
        WHERE id = %s
        RETURNING id, user_id, username, fullname, name, surname, room, status,
                  processed_by, processed_by_fullname, processed_by_username,
                  refuse_reason, created_at, image, lang
    """

    logger.trace_db(query, values)

    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, values)
            row = await cur.fetchone()
            await conn.commit()

            if row:
                return Resident(
                    id=row[0],
                    user_id=row[1],
                    username=row[2],
                    fullname=row[3],
                    name=row[4],
                    surname=row[5],
                    room=row[6],
                    status=row[7],
                    processed_by=row[8],
                    processed_by_fullname=row[9],
                    processed_by_username=row[10],
                    refuse_reason=row[11],
                    created_at=row[12],
                    image=row[13],
                    lang=row[14]
                )
            return None


async def delete_resident_by_user_id(user_id: int) -> bool:
    """
    Удаляет пользователя из таблицы users по Telegram user_id.
    Возвращает True, если запись существовала и была удалена, иначе False.
    """
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = "DELETE FROM residents WHERE user_id = %s RETURNING id"
            values = (user_id,)
            logger.trace_db(query, values)
            await cur.execute(
                query,
                values
            )
            row = await cur.fetchone()
            await conn.commit()
            return row is not None


async def delete_residents_by_user_id(user_id: int) -> int:
    """
    Удаляет все записи из таблицы users с указанным Telegram user_id.
    Возвращает количество удалённых строк.
    """
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = "DELETE FROM residents WHERE user_id = %s"
            values = (user_id,)
            logger.trace_db(query, values)
            await cur.execute(
                query,
                values
            )
            deleted_count = cur.rowcount  # количество удалённых строк
            await conn.commit()
            return deleted_count


async def create_or_replace_request(user_id: int, greeting_msg: int, lang: str) -> None:
    """
    Создаёт запись в таблице requests для указанного user_id.
    Если запись уже есть — удаляет её и вставляет заново с дефолтными значениями.
    """
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            # Сначала удаляем, если есть
            delete_query = "DELETE FROM requests WHERE user_id = %s"
            delete_values = (user_id,)
            logger.trace_db(delete_query, delete_values)
            await cur.execute(delete_query, delete_values)

            # Теперь вставляем новую запись
            insert_query = """
                           INSERT INTO requests (user_id, greeting_msg, lang)
                           VALUES (%s, %s, %s) \
                           """
            insert_values = (user_id, greeting_msg, lang)
            logger.trace_db(insert_query, insert_values)
            await cur.execute(insert_query, insert_values)
            await conn.commit()


@dataclass(frozen=True)
class RequestInfo:
    user_id: int
    created_at: datetime
    greeting_msg: int
    lang: str


async def pop_unprocessed_requests_older_than(hours: int) -> FrozenSet[RequestInfo]:
    """
    Находит все записи, у которых processed = FALSE и created_at старше указанного количества часов.
    Помечает их processed = TRUE и возвращает список в виде множества RequestInfo.
    """
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = """
                    UPDATE requests
                    SET processed = TRUE
                    WHERE processed = FALSE
                      AND created_at <= NOW() - (%s * INTERVAL '1 hour') 
                    RETURNING user_id, created_at, greeting_msg, lang \
                    """
            values = (hours,)
            logger.trace_db(query, values)
            await cur.execute(query, values)
            rows = await cur.fetchall()

            await conn.commit()

            return frozenset(
                RequestInfo(user_id=row[0], created_at=row[1], greeting_msg=row[2], lang=row[3]) for row in rows
            )


async def mark_request_processed(user_id: int) -> int:
    """
    Обновляет processed = TRUE у записи по user_id.
    Возвращает количество обновлённых строк.
    """
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = """
                    UPDATE requests
                    SET processed = TRUE
                    WHERE user_id = %s \
                    """
            values = (user_id,)
            logger.trace_db(query, values)
            await cur.execute(query, values)
            updated_count = cur.rowcount
            await conn.commit()
            return updated_count
