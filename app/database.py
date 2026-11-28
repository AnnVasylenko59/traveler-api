import os
import re
import sys
import types
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
pool: AsyncConnectionPool | None = None

def _convert_sql(query: str) -> str:
    return re.sub(r'\$(\d+)', r'%s', query)

class CompatConnection:
    def __init__(self, conn: psycopg.AsyncConnection):
        self._conn = conn

    async def fetch(self, query: str, *args):
        async with self._conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(_convert_sql(query), args)
            return await cur.fetchall()

    async def fetchrow(self, query: str, *args):
        async with self._conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(_convert_sql(query), args)
            return await cur.fetchone()

    async def fetchval(self, query: str, *args):
        async with self._conn.cursor() as cur:
            await cur.execute(_convert_sql(query), args)
            row = await cur.fetchone()
            return row[0] if row else None

    async def execute(self, query: str, *args):
        async with self._conn.cursor() as cur:
            await cur.execute(_convert_sql(query), args)
            return cur.statusmessage or ""

    def transaction(self):
        return self._conn.transaction()

# Емуляція модуля asyncpg для анотацій типів і винятків у роутерах
_compat_asyncpg = types.ModuleType("asyncpg")
_compat_asyncpg.Connection = CompatConnection
_compat_asyncpg.CheckViolationError = psycopg.errors.CheckViolation
_compat_asyncpg.DataError = psycopg.errors.DataError
_compat_asyncpg.IntegrityConstraintViolationError = psycopg.errors.IntegrityError
sys.modules["asyncpg"] = _compat_asyncpg


async def create_pool():
    global pool
    pool = AsyncConnectionPool(
        conninfo=DATABASE_URL,
        min_size=10,
        max_size=50,
        open=False,
        kwargs={"autocommit": True, "prepare_threshold": None}
    )
    await pool.open()
    print("Database pool created (psycopg + PgCat)!")


async def close_pool():
    global pool
    if pool:
        await pool.close()
        print("Database pool closed!")


async def get_db_connection():
    async with pool.connection() as conn:
        yield CompatConnection(conn)