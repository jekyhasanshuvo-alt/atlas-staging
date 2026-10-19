from logging.config import fileConfig

from alembic import context
from app.core.config import Settings
from app.db.base import Base
from app.db.session import build_engine
from app.models import (
    catalog,  # noqa: F401
    student,  # noqa: F401
)

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata
if context.is_offline_mode():
    context.configure(
        url=Settings().database_url.get_secret_value(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    supplied = config.attributes.get("connection")

    def migrate(connection):
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()

    if supplied is not None:
        migrate(supplied)
    else:
        engine = build_engine(Settings())
        with engine.connect() as connection:
            migrate(connection)
        engine.dispose()
