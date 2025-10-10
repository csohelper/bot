from dataclasses import dataclass

from python.logger import logger
from python.storage import database


async def init_database_module() -> None:
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = """
                CREATE TABLE IF NOT EXISTS anecdotes (
                    id SERIAL PRIMARY KEY,
                    anecdote_id INTEGER NOT NULL UNIQUE,
                    original TEXT,
                    text TEXT,
                    used BOOLEAN NOT NULL DEFAULT FALSE
                )
            """
            logger.debug_db(query)
            await cur.execute(query)
            await conn.commit()


@dataclass(frozen=True)
class AnecdoteItem:
    id: int
    anecdote_id: int
    original: str | None
    text: str | None
    used: bool


async def poll_anecdote() -> AnecdoteItem | None:
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = """
                    UPDATE anecdotes
                    SET used = TRUE
                    WHERE id = (SELECT id
                                FROM anecdotes
                                WHERE used IS FALSE
                                ORDER BY id
                                LIMIT 1 FOR UPDATE SKIP LOCKED)
                    RETURNING id, anecdote_id, original, text, used; \
                    """
            logger.debug_db(query)
            await cur.execute(query)
            row = await cur.fetchone()
            if row:
                return AnecdoteItem(
                    id=row[0],
                    anecdote_id=row[1],
                    original=row[2],
                    text=row[3],
                    used=row[4]
                )
            return None


async def count_unused_anecdotes() -> int:
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = """
                SELECT COUNT(*) FROM anecdotes WHERE used IS FALSE;
            """
            logger.debug_db(query)
            await cur.execute(query)
            (count,) = await cur.fetchone()
            return count


async def insert_anecdote(anecdote_id: int, original: str, text: str) -> None:
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = """
                INSERT INTO anecdotes (anecdote_id, original, text, used)
                VALUES (%s, %s, %s, FALSE)
                ON CONFLICT (anecdote_id) DO UPDATE
                SET original = EXCLUDED.original,
                    text = EXCLUDED.text,
                    used = FALSE
            """
            values = (anecdote_id, original, text)
            logger.debug_db(query, values)
            await cur.execute(query, values)
            await conn.commit()
