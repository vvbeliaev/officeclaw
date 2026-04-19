import asyncio

from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

from src.shared.config import get_settings

config = context.config
fileConfig(config.config_file_name)

_sa_url = (
    get_settings().database_url
    .replace("postgresql://", "postgresql+asyncpg://", 1)
    .replace("postgres://", "postgresql+asyncpg://", 1)
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


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(_sa_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
