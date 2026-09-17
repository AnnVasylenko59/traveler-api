import os
import asyncpg
from dotenv import load_dotenv

# Завантажуємо змінні середовища з файлу .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Глобальна змінна для нашого пулу з'єднань
pool = None

async def create_pool():
    global pool
    # min_size та max_size допомагають впоратись з навантаженням (1000+ користувачів)
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
    print("Database pool created!")

async def close_pool():
    global pool
    if pool:
        await pool.close()
        print("Database pool closed!")

# Ця функція буде використовуватись у наших роутерах для отримання з'єднання
async def get_db_connection():
    async with pool.acquire() as connection:
        yield connection