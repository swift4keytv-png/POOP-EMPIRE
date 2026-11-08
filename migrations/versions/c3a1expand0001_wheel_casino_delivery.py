"""Колесо, казино, заводы и поля доставки.

Revision ID: c3a1expand0001
Revises: b6dfc6f47e43
"""

import sqlalchemy as sa
from alembic import op

revision = "c3a1expand0001"
down_revision = "b6dfc6f47e43"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("poop_coins", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("xp", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("extra_spins", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("free_deliveries", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("last_daily_spin", sa.Date(), nullable=True))
        batch.add_column(sa.Column("last_daily_coins", sa.Date(), nullable=True))
    with op.batch_alter_table("orders") as batch:
        batch.add_column(sa.Column("delivery_stage", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("next_stage_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("stage_updated_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("delivery_demo", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("courier_name", sa.String(length=120), nullable=True, server_default="Сергей Любин"))


def downgrade():
    pass
