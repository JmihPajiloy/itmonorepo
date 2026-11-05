from alembic import context

from app.config import settings
from app.db import Base, engine
from app import models  # noqa: F401 — регистрация метаданных

config = context.config


def migrate(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url=settings.database_url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    migrate(config.attributes["connection"])
else:
    with engine.connect() as connection:
        migrate(connection)
