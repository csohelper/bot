from contextlib import asynccontextmanager
from psycopg_pool import AsyncConnectionPool

import python.logger

db_pool: AsyncConnectionPool | None = None


def logger():
    return python.logger.logger


async def open_database_pool() -> None:
    global db_pool
    from .config import config
    conninfo = (f"host={config.database.host} "
                f"dbname={config.database.database} "
                f"user={config.database.user} "
                f"password={config.database.password} "
                f"port={config.database.port}")
    db_pool = AsyncConnectionPool(
        conninfo=conninfo,
        min_size=config.database.min_pool_size,
        max_size=config.database.max_pool_size,
        open=False
    )
    await db_pool.open()
    await test_database_connection()
    logger().info("Database: DB connection pool started")


async def close_database_pool() -> None:
    if db_pool:
        await db_pool.close()
        logger().info("Database: DB connection pool closed")


@asynccontextmanager
async def get_db_connection():
    if db_pool is None:
        logger().error("Database: Pool is not initialized. Call open_database_pool first.")
        # В реальном приложении лучше вызвать исключение, а не exit(1)
        raise RuntimeError("Database pool not initialized.")
    async with db_pool.connection() as conn:
        yield conn


async def test_database_connection():
    if db_pool is None:
        logger().error("Database: Pool is not initialized. Call open_database_pool first.")
        exit(1)
    try:
        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1;")
                result = await cur.fetchone()
                if result and result[0] == 1:
                    logger().info("Database: successful connection to the DB has been confirmed.")
                else:
                    logger().warning(
                        "Database: the connection is established, "
                        "but the test request did not give the expected result..")
    except Exception as e:
        logger().error(f"Database: Error when checking the connection to the database: {e}")
        exit(1)
