from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from python.logger import logger
from python.storage import database


@dataclass(frozen=True)
class User:
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


async def init_database_module() -> None:
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL UNIQUE,
                    username TEXT NOT NULL,
                    fullname TEXT NOT NULL,
                    name TEXT NOT NULL,
                    surname TEXT NOT NULL,
                    room INTEGER,
                    status TEXT DEFAULT 'moderation',
                    processed_by BIGINT,
                    processed_by_fullname TEXT,
                    processed_by_username TEXT,
                    refuse_reason TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """
            logger.debug((query,))
            await cur.execute(query)
            await conn.commit()


async def add_user(
        user_id: int,
        username: str,
        fullname: str,
        name: str,
        surname: str,
        room: int | None = None,
        status: str = "waiting"
) -> int:
    """
    Добавляет пользователя в таблицу users или обновляет его данные.
    Возвращает id (PRIMARY KEY) из таблицы users.

    :param user_id: Telegram user_id
    :param username: username (без @)
    :param fullname: Полное имя из Telegram
    :param name: Имя (из анкеты)
    :param surname: Фамилия (из анкеты)
    :param room: Комната (может быть None)
    :param status: Статус (по умолчанию 'waiting')
    :return: id записи в таблице users
    """
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = """
                INSERT INTO users (user_id, username, fullname, name, surname, room, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            values = (user_id, username, fullname, name, surname, room, status)
            logger.debug((query, values))
            await cur.execute(query, values)
            row = await cur.fetchone()
            await conn.commit()
            return row[0]


async def get_user_by_id(user_id: int) -> User | None:
    """
    Возвращает пользователя из таблицы users по его id (PRIMARY KEY).

    :param user_id: id из таблицы users (не Telegram user_id!)
    :return: User или None, если не найден
    """
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = """
                SELECT id, user_id, username, fullname, name, surname, room, status,
                       processed_by, processed_by_fullname, processed_by_username,
                       refuse_reason, created_at
                FROM users
                WHERE id = %s
            """
            logger.debug((query, (user_id,)))
            await cur.execute(
                query,
                (user_id,)
            )
            row = await cur.fetchone()

            if not row:
                return None

            return User(
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
            )


ALLOWED_USER_FIELDS = {
    "username", "fullname", "name", "surname", "room", "status",
    "processed_by", "processed_by_fullname", "processed_by_username",
    "refuse_reason"
}

async def update_user_fields(id: int, **fields) -> Optional[User]:
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
    values.append(id)

    query = f"""
        UPDATE users
        SET {set_clause}
        WHERE id = %s
        RETURNING id, user_id, username, fullname, name, surname, room, status,
                  processed_by, processed_by_fullname, processed_by_username,
                  refuse_reason, created_at
    """

    logger.debug((query, values))

    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, values)
            row = await cur.fetchone()
            await conn.commit()

            if row:
                return User(
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
                )
            return None


async def delete_user_by_user_id(user_id: int) -> bool:
    """
    Удаляет пользователя из таблицы users по Telegram user_id.
    Возвращает True, если запись существовала и была удалена, иначе False.
    """
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = "DELETE FROM users WHERE user_id = %s RETURNING id"
            logger.debug((query, (user_id,)))
            await cur.execute(
                query,
                (user_id,)
            )
            row = await cur.fetchone()
            await conn.commit()
            return row is not None


async def delete_users_by_user_id(user_id: int) -> int:
    """
    Удаляет все записи из таблицы users с указанным Telegram user_id.
    Возвращает количество удалённых строк.
    """
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = "DELETE FROM users WHERE user_id = %s"
            logger.debug((query, (user_id,)))
            await cur.execute(
                query,
                (user_id,)
            )
            deleted_count = cur.rowcount  # количество удалённых строк
            await conn.commit()
            return deleted_count
