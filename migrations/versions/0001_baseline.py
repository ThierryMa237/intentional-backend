"""Schéma de départ (état après la PR #1)

Les bases existantes ont été créées par `Base.metadata.create_all` sans Alembic.
Cette migration ne crée donc que les tables manquantes : elle passe sans erreur
sur une base vide comme sur une base déjà en production.

Revision ID: 0001
Revises:
Create Date: 2026-10-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("phone", sa.String(20), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("hashed_password", sa.String(255), nullable=False),
        )

    if "hangouts" not in existing:
        op.create_table(
            "hangouts",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("creator_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column("confirmed_slot", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    if "hangout_participants" not in existing:
        op.create_table(
            "hangout_participants",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("hangout_id", sa.Uuid(), sa.ForeignKey("hangouts.id"), nullable=False),
            sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("joined_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("hangout_id", "user_id", name="uq_hangout_user"),
        )

    if "availabilities" not in existing:
        op.create_table(
            "availabilities",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("hangout_id", sa.Uuid(), sa.ForeignKey("hangouts.id"), nullable=False),
            sa.Column("slot_start", sa.DateTime(), nullable=False),
            sa.Column("slot_end", sa.DateTime(), nullable=False),
        )

    # Rattrapage (repris de l'ancien main.py) : chaque créateur est participant
    op.execute("""
        INSERT INTO hangout_participants (id, hangout_id, user_id, joined_at)
        SELECT gen_random_uuid(), h.id, h.creator_id, h.created_at
        FROM hangouts h
        WHERE NOT EXISTS (
            SELECT 1 FROM hangout_participants p
            WHERE p.hangout_id = h.id AND p.user_id = h.creator_id
        )
    """)


def downgrade() -> None:
    op.drop_table("availabilities")
    op.drop_table("hangout_participants")
    op.drop_table("hangouts")
    op.drop_table("users")
