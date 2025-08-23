import time

from functools import wraps

from app.core.config import settings

def timeit(func):
    """
    Декоратор для определения времени выполнения методов и функций
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        processing_time = end_time - start_time
        print(f"Время обработки {func.__name__}: {processing_time:.2f} секунд")
        return result
    return wrapper

def get_url_db():
    """
    Вспомогательная функция для формирования строки подключения к БД

    :return:
    """

    # Alembic требует синхронный драйвер, поэтому заменяем asyncpg на psycopg2
    url = settings.ASYNC_DATABASE_URI
    if url and "asyncpg" in url:
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    return url