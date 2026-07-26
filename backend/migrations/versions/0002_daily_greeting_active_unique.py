"""Enforce one active daily greeting per user, type, and business date."""

import logging

import sqlalchemy as sa
from alembic import op

revision = "0002_daily_greeting_unique"
down_revision = "0001_existing_mysql_baseline"
branch_labels = None
depends_on = None

LOGGER = logging.getLogger("alembic.daily_greeting_active_unique")
ACTIVE_USER_COLUMN = "active_user_id"
ACTIVE_GREETING_INDEX = "uk_daily_greeting_active_user_type_date"


def _group_count(query: str) -> int:
    value = op.get_bind().scalar(sa.text(query))
    return int(value or 0)


def _schema_object_count(query: str, **parameters: str) -> int:
    value = op.get_bind().scalar(sa.text(query), parameters)
    return int(value or 0)


def upgrade() -> None:
    LOGGER.info("event=daily_greeting_unique_migration_started operation=upgrade result=started")
    duplicate_greeting_groups = _group_count(
        """
        SELECT COUNT(*)
        FROM (
            SELECT 1
            FROM t_daily_greeting
            WHERE is_deleted = 0
            GROUP BY user_id, greeting_type, greeting_date
            HAVING COUNT(*) > 1
        ) AS duplicate_greetings
        """
    )
    duplicate_streak_groups = _group_count(
        """
        SELECT COUNT(*)
        FROM (
            SELECT 1
            FROM t_greeting_streak
            GROUP BY couple_id, streak_type
            HAVING COUNT(*) > 1
        ) AS duplicate_streaks
        """
    )
    invalid_delete_rows = _group_count(
        """
        SELECT COUNT(*)
        FROM t_daily_greeting
        WHERE is_deleted IS NULL OR is_deleted NOT IN (0, 1)
        """
    )
    streak_unique_indexes = _group_count(
        """
        SELECT COUNT(*)
        FROM (
            SELECT index_name
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = 't_greeting_streak'
              AND non_unique = 0
            GROUP BY index_name
            HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index)
                = 'couple_id,streak_type'
        ) AS matching_streak_indexes
        """
    )
    active_user_columns = _schema_object_count(
        """
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = 't_daily_greeting'
          AND column_name = :column_name
        """,
        column_name=ACTIVE_USER_COLUMN,
    )
    active_greeting_index_columns = _schema_object_count(
        """
        SELECT COUNT(*)
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = 't_daily_greeting'
          AND index_name = :index_name
          AND non_unique = 0
        """,
        index_name=ACTIVE_GREETING_INDEX,
    )
    LOGGER.info(
        "event=daily_greeting_unique_preflight_completed operation=upgrade result=checked "
        "duplicateGreetingGroupCount=%s duplicateStreakGroupCount=%s "
        "invalidDeleteRowCount=%s streakUniqueIndexCount=%s activeUserColumnCount=%s "
        "activeGreetingIndexColumnCount=%s",
        duplicate_greeting_groups,
        duplicate_streak_groups,
        invalid_delete_rows,
        streak_unique_indexes,
        active_user_columns,
        active_greeting_index_columns,
    )
    if (
        duplicate_greeting_groups
        or duplicate_streak_groups
        or invalid_delete_rows
        or streak_unique_indexes != 1
        or active_user_columns not in (0, 1)
        or active_greeting_index_columns not in (0, 3)
        or (active_greeting_index_columns == 3 and active_user_columns == 0)
    ):
        LOGGER.error(
            "event=daily_greeting_unique_migration_rejected operation=upgrade "
            "result=rejected errorCode=SCHEMA_PREFLIGHT_FAILED"
        )
        raise RuntimeError("Daily greeting unique migration preflight failed")

    if active_user_columns == 0:
        op.add_column(
            "t_daily_greeting",
            sa.Column(
                ACTIVE_USER_COLUMN,
                sa.BigInteger(),
                sa.Computed(
                    "CASE WHEN is_deleted = 0 THEN user_id ELSE NULL END", persisted=True
                ),
                nullable=True,
            ),
        )
        LOGGER.info(
            "event=daily_greeting_active_user_column_added operation=upgrade result=success"
        )
    else:
        LOGGER.info(
            "event=daily_greeting_active_user_column_skipped operation=upgrade "
            "result=already_exists"
        )

    if active_greeting_index_columns == 0:
        op.create_index(
            ACTIVE_GREETING_INDEX,
            "t_daily_greeting",
            [ACTIVE_USER_COLUMN, "greeting_type", "greeting_date"],
            unique=True,
        )
        LOGGER.info(
            "event=daily_greeting_active_unique_index_created operation=upgrade result=success"
        )
    else:
        LOGGER.info(
            "event=daily_greeting_active_unique_index_skipped operation=upgrade "
            "result=already_exists"
        )
    LOGGER.info("event=daily_greeting_unique_migration_completed operation=upgrade result=success")


def downgrade() -> None:
    LOGGER.warning(
        "event=daily_greeting_unique_migration_downgrade_started operation=downgrade result=started"
    )
    op.drop_index(ACTIVE_GREETING_INDEX, table_name="t_daily_greeting")
    op.drop_column("t_daily_greeting", ACTIVE_USER_COLUMN)
    LOGGER.warning(
        "event=daily_greeting_unique_migration_downgrade_completed operation=downgrade "
        "result=success"
    )
