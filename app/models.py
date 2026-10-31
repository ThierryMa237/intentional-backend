from sqlalchemy import Column, String, Text, DateTime, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone
from app.database import Base

# --- Valeurs autorisées (alignées sur la maquette JxC-Lab/Intentional) ---

# Puces "type du hangout" de l'écran Nouveau hangout
HANGOUT_TYPES = (
    "Diner", "Café", "Cinéma", "Sport", "Journaling",
    "Administratif", "Co-working", "Sunday Brunch",
)
# Bascule Planifié / Improvisé
HANGOUT_MODES = ("planned", "spontaneous")
# Choix du lieu : Réservation (partenaire) ou Libre
PLACE_KINDS = ("reservation", "free")
# Statut global du hangout
HANGOUT_STATUSES = ("pending", "confirmed", "cancelled")
# Réponse de chaque participant : En attente / Accepter / Indisponible
PARTICIPANT_STATUSES = ("pending", "accepted", "declined")


def utcnow() -> datetime:
    """Heure UTC sans fuseau (les colonnes DateTime sont naïves, en UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    hashed_password = Column(String(255), nullable=False)


class Hangout(Base):
    __tablename__ = "hangouts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    creator_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    confirmed_slot = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    # Détails (écran Nouveau hangout / carte d'invitation)
    hangout_type = Column(String(30), nullable=True)
    mode = Column(String(20), default="planned", nullable=False)
    place_name = Column(String(200), nullable=True)
    place_kind = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    message = Column(String(280), nullable=True)
    # Fenêtre proposée (Début / Fin) dans laquelle le matching cherche un créneau
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)

    creator = relationship("User")
    participants = relationship(
        "HangoutParticipant", back_populates="hangout", cascade="all, delete-orphan"
    )


class HangoutParticipant(Base):
    __tablename__ = "hangout_participants"
    __table_args__ = (UniqueConstraint("hangout_id", "user_id", name="uq_hangout_user"),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    hangout_id = Column(Uuid, ForeignKey("hangouts.id"), nullable=False)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=utcnow)
    status = Column(String(20), default="pending", nullable=False)
    responded_at = Column(DateTime, nullable=True)

    hangout = relationship("Hangout", back_populates="participants")
    user = relationship("User")


class Availability(Base):
    __tablename__ = "availabilities"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    hangout_id = Column(Uuid, ForeignKey("hangouts.id"), nullable=False)
    slot_start = Column(DateTime, nullable=False)
    slot_end = Column(DateTime, nullable=False)

    user = relationship("User")
    hangout = relationship("Hangout")
