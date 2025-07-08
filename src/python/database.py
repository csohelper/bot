from psycopg_pool import AsyncConnectionPool
from .config import config
from .logger import logger


db_pool = None


async def open_database_pool() -> None:
    global db_pool
    conninfo = f"host={config.database.host} dbname={config.database.database} user={config.database.user} password={config.database.password} port={config.database.port}"
    db_pool = AsyncConnectionPool(
        conninfo=conninfo,
        min_size=config.database.min_pool_size,
        max_size=config.database.max_pool_size,
        open=False
    )
    await db_pool.open()
    await test_database_connection()
    logger.info("Database: DB connection pool started")


async def close_database_pool() -> None:
    if db_pool:
        await db_pool.close()
        logger.info("Database: DB connection pool closed")


async def get_db_connection():
    if db_pool is None:
        logger.error("Database: Pool is not initialized. Call open_database_pool first.")
        exit(1)
    async with db_pool.connection() as conn:
        yield conn


async def test_database_connection():
    if db_pool is None:
        logger.error("Database: Pool is not initialized. Call open_database_pool first.")
        exit(1)
    try:
        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1;")
                result = await cur.fetchone()
                if result and result[0] == 1:
                    logger.info("Database: successful connection to the DB has been confirmed.")
                else:
                    logger.warning("Database: the connection is established, but the test request did not give the expected result..")
    except Exception as e:
        logger.error(f"Database: Error when checking the connection to the database: {e}")
        exit(1)