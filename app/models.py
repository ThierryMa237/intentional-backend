from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone
from app.database import Base


def utcnow() -> datetime:
    """Heure UTC sans fuseau (les colonnes DateTime sont naïves, en UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    hashed_password = Column(String(255), nullable=False)


class Hangout(Base):
    __tablename__ = "hangouts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    status = Column(String(20), default="pending")  # pending, confirmed, cancelled
    confirmed_slot = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    creator = relationship("User")
    participants = relationship(
        "HangoutParticipant", back_populates="hangout", cascade="all, delete-orphan"
    )


class HangoutParticipant(Base):
    __tablename__ = "hangout_participants"
    __table_args__ = (UniqueConstraint("hangout_id", "user_id", name="uq_hangout_user"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hangout_id = Column(UUID(as_uuid=True), ForeignKey("hangouts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=utcnow)

    hangout = relationship("Hangout", back_populates="participants")
    user = relationship("User")


class Availability(Base):
    __tablename__ = "availabilities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    hangout_id = Column(UUID(as_uuid=True), ForeignKey("hangouts.id"), nullable=False)
    slot_start = Column(DateTime, nullable=False)
    slot_end = Column(DateTime, nullable=False)

    user = relationship("User")
    hangout = relationship("Hangout")
