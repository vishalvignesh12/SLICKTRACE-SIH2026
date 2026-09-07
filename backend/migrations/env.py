import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Import settings and target metadata
from app.core.config import settings
from app.models import Base

# Alembic Config object
config = context.config

# Debug: print tables in metadata
print("Tables in metadata:", list(Base.metadata.tables.keys()))

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set database URL dynamically from app settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata

def include_object(object, name, type_, reflected, compare_to):
    """Filter out PostGIS extension system tables and reflected spatial indexes from autogenerate/check."""
    if type_ == "table":
        app_tables = {
            "incidents", "users", "vessels", "ais_tracks", "satellite_scenes",
            "slick_detections", "drift_results", "attribution_scores", "ml_inference_log",
            "investigations", "investigation_events", "spill_regions",
            "alembic_version"
        }
        if name not in app_tables:
            return False
    if type_ == "index" and reflected:
        # Ignore reflected PostGIS spatial indexes
        if name in {
            "ix_scenes_bbox", "ix_incidents_location", "ix_ais_tracks_position",
            "ix_slick_detections_geometry", "ix_drift_results_origin_point",
            "street_type_lookup_abbrev_idx", "direction_lookup_abbrev_idx",
            "idx_tiger_county", "countysub_lookup_name_idx", "countysub_lookup_state_idx",
            "secondary_unit_lookup_abbrev_idx", "tige_cousub_the_geom_gist"
        }:
            return False
    return True

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
