"""Register the audited pre-FastAPI MySQL schema without changing it."""

revision = "0001_existing_mysql_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    raise RuntimeError("Existing production baseline cannot be downgraded")
