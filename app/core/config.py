from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / '.env'


class Settings(BaseSettings):
    """Настройки приложения для загрузки из .env и окружения."""

    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str

    elasticsearch_host: str
    elasticsearch_port: int
    elasticsearch_index: str = 'documents'

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding='utf-8',
        extra='ignore',
    )

    sse_keepalive_interval: int = 15


@lru_cache
def get_settings() -> Settings:
    """Возвращает объект настроек из кэша."""
    return Settings()


settings = get_settings()


def get_db_url() -> str:
    """Формирует путь для подключения к БД."""
    return (
        f'postgresql+asyncpg://{settings.postgres_user}:'
        f'{settings.postgres_password}@{settings.postgres_host}:'
        f'{settings.postgres_port}/{settings.postgres_db}'
    )
