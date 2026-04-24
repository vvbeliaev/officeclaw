from logging.config import fileConfig

from sqlalchemy import create_engine
from alembic import context

from src.shared.config import get_settings

config = context.config
fileConfig(config.config_file_name)

_sa_url = (
    get_settings().database_url
    .replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    .replace("postgres://", "postgresql+psycopg://", 1)
    .replace("postgresql://", "postgresql+psycopg://", 1)
)
config.set_main_option("sqlalchemy.url", _sa_url)

target_metadata = None


def run_migrations_offline() -> None:
    context.configure(
        url=_sa_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_sa_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
