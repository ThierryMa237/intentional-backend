"""Détails des hangouts et réponses aux invitations (maquette JxC-Lab/Intentional)

- hangouts : type, mode planifié/improvisé, lieu, description, image, message,
  fenêtre début/fin
- hangout_participants : statut de réponse (pending / accepted / declined)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("hangouts", sa.Column("hangout_type", sa.String(30), nullable=True))
    op.add_column("hangouts", sa.Column(
        "mode", sa.String(20), nullable=False, server_default="planned"))
    op.add_column("hangouts", sa.Column("place_name", sa.String(200), nullable=True))
    op.add_column("hangouts", sa.Column("place_kind", sa.String(20), nullable=True))
    op.add_column("hangouts", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("hangouts", sa.Column("image_url", sa.String(500), nullable=True))
    op.add_column("hangouts", sa.Column("message", sa.String(280), nullable=True))
    op.add_column("hangouts", sa.Column("start_at", sa.DateTime(), nullable=True))
    op.add_column("hangouts", sa.Column("end_at", sa.DateTime(), nullable=True))

    op.execute("UPDATE hangouts SET status = 'pending' WHERE status IS NULL")
    op.alter_column("hangouts", "status", nullable=False, server_default="pending")

    op.add_column("hangout_participants", sa.Column(
        "status", sa.String(20), nullable=False, server_default="pending"))
    op.add_column("hangout_participants", sa.Column("responded_at", sa.DateTime(), nullable=True))

    # Données existantes : le créateur a forcément accepté, et un·e invité·e qui
    # avait déjà donné ses disponibilités est considéré·e comme ayant accepté.
    op.execute("""
        UPDATE hangout_participants p SET status = 'accepted', responded_at = p.joined_at
        FROM hangouts h
        WHERE p.hangout_id = h.id AND p.user_id = h.creator_id
    """)
    op.execute("""
        UPDATE hangout_participants p SET status = 'accepted', responded_at = p.joined_at
        WHERE p.status = 'pending' AND EXISTS (
            SELECT 1 FROM availabilities a
            WHERE a.hangout_id = p.hangout_id AND a.user_id = p.user_id
        )
    """)


def downgrade() -> None:
    op.drop_column("hangout_participants", "responded_at")
    op.drop_column("hangout_participants", "status")
    op.alter_column("hangouts", "status", nullable=True, server_default=None)
    for col in ("end_at", "start_at", "message", "image_url", "description",
                "place_kind", "place_name", "mode", "hangout_type"):
        op.drop_column("hangouts", col)
