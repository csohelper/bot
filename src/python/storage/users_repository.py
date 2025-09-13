from dataclasses import dataclass
from typing import Optional

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


async def init_database_module() -> None:
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    fullname TEXT NOT NULL,
                    name TEXT NOT NULL,
                    surname TEXT NOT NULL,
                    room INTEGER,
                    status TEXT DEFAULT 'moderation'
                )
            """)
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
            await cur.execute(
                """
                INSERT INTO users (user_id, username, fullname, name, surname, room, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET username = EXCLUDED.username,
                    fullname = EXCLUDED.fullname,
                    name = EXCLUDED.name,
                    surname = EXCLUDED.surname,
                    room = EXCLUDED.room,
                    status = EXCLUDED.status
                RETURNING id
                """,
                (user_id, username, fullname, name, surname, room, status)
            )
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
            await cur.execute(
                """
                SELECT id, user_id, username, fullname, name, surname, room, status
                FROM users
                WHERE id = %s
                """,
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
            )
