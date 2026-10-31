from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from datetime import datetime, timezone
from typing import Optional
import uuid

from app.database import get_db
from app import models
from app.auth import get_current_user
from app.matching import find_common_slots
from app.schemas import PHONE_PATTERN

router = APIRouter(prefix="/hangouts", tags=["hangouts"])


# ---------- Schémas ----------

class HangoutCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class HangoutOut(BaseModel):
    id: uuid.UUID
    creator_id: uuid.UUID
    title: str
    status: str
    created_at: datetime
    confirmed_slot: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ParticipantAdd(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN)


def _to_naive_utc(dt: datetime) -> datetime:
    """Les colonnes DateTime sont sans fuseau : on stocke tout en UTC naïf."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class AvailabilityCreate(BaseModel):
    slot_start: datetime
    slot_end: datetime

    @field_validator("slot_start", "slot_end")
    @classmethod
    def normalize_tz(cls, v: datetime) -> datetime:
        return _to_naive_utc(v)

    @model_validator(mode="after")
    def check_range(self):
        if self.slot_end <= self.slot_start:
            raise ValueError("slot_end doit être après slot_start")
        if self.slot_end <= models.utcnow():
            raise ValueError("La disponibilité est déjà passée")
        return self


# ---------- Helpers ----------

def _get_hangout_or_404(db: Session, hangout_id: uuid.UUID) -> models.Hangout:
    hangout = db.query(models.Hangout).filter(models.Hangout.id == hangout_id).first()
    if not hangout:
        raise HTTPException(status_code=404, detail="Hangout introuvable")
    return hangout


def _participant_ids(db: Session, hangout_id: uuid.UUID) -> set:
    rows = db.query(models.HangoutParticipant.user_id).filter(
        models.HangoutParticipant.hangout_id == hangout_id
    ).all()
    return {r[0] for r in rows}


def _require_participant(db: Session, hangout: models.Hangout, user: models.User) -> None:
    # 404 plutôt que 403 : on ne révèle pas l'existence d'un hangout aux non-membres
    if user.id not in _participant_ids(db, hangout.id):
        raise HTTPException(status_code=404, detail="Hangout introuvable")


def _require_creator(hangout: models.Hangout, user: models.User) -> None:
    if hangout.creator_id != user.id:
        raise HTTPException(status_code=403, detail="Seul le créateur peut faire cette action")


def _require_pending(hangout: models.Hangout) -> None:
    if hangout.status != "pending":
        raise HTTPException(
            status_code=409, detail=f"Hangout déjà {hangout.status}, action impossible"
        )


# ---------- Routes ----------

@router.post("/", response_model=HangoutOut)
def create_hangout(
    hangout: HangoutCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    new_hangout = models.Hangout(title=hangout.title, creator_id=current_user.id)
    # Le créateur est automatiquement participant
    new_hangout.participants.append(models.HangoutParticipant(user_id=current_user.id))
    db.add(new_hangout)
    db.commit()
    db.refresh(new_hangout)
    return new_hangout


@router.get("/", response_model=list[HangoutOut])
def list_hangouts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Hangouts dont l'utilisateur est participant (créés ou invités)."""
    return (
        db.query(models.Hangout)
        .join(models.HangoutParticipant)
        .filter(models.HangoutParticipant.user_id == current_user.id)
        .order_by(models.Hangout.created_at.desc())
        .all()
    )


@router.post("/{hangout_id}/participants")
def add_participant(
    hangout_id: uuid.UUID,
    participant: ParticipantAdd,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Le créateur invite un utilisateur inscrit via son numéro de téléphone."""
    hangout = _get_hangout_or_404(db, hangout_id)
    _require_participant(db, hangout, current_user)
    _require_creator(hangout, current_user)
    _require_pending(hangout)

    user = db.query(models.User).filter(models.User.phone == participant.phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="Aucun utilisateur avec ce numéro")
    if user.id in _participant_ids(db, hangout_id):
        return {"message": "Déjà participant"}

    db.add(models.HangoutParticipant(hangout_id=hangout_id, user_id=user.id))
    db.commit()
    return {"message": "Participant ajouté"}


@router.post("/{hangout_id}/availabilities")
def add_availability(
    hangout_id: uuid.UUID,
    availability: AvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    hangout = _get_hangout_or_404(db, hangout_id)
    _require_participant(db, hangout, current_user)
    _require_pending(hangout)

    db.add(models.Availability(
        user_id=current_user.id,
        hangout_id=hangout_id,
        slot_start=availability.slot_start,
        slot_end=availability.slot_end,
    ))
    db.commit()
    return {"message": "Disponibilité ajoutée"}


@router.post("/{hangout_id}/match")
def match_hangout(
    hangout_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    hangout = _get_hangout_or_404(db, hangout_id)
    _require_participant(db, hangout, current_user)
    _require_creator(hangout, current_user)
    _require_pending(hangout)

    participants = _participant_ids(db, hangout_id)
    if len(participants) < 2:
        raise HTTPException(status_code=400, detail="Il faut au moins 2 participants")

    availabilities_db = db.query(models.Availability).filter(
        models.Availability.hangout_id == hangout_id
    ).all()

    # Regrouper par utilisateur (seulement les participants actuels)
    avail_dict: dict = {}
    for a in availabilities_db:
        if a.user_id in participants:
            avail_dict.setdefault(a.user_id, []).append((a.slot_start, a.slot_end))

    missing = participants - set(avail_dict)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"{len(missing)} participant(s) n'ont pas encore donné leurs disponibilités",
        )

    now = models.utcnow()
    common_slots = [s for s in find_common_slots(avail_dict) if s >= now]

    if not common_slots:
        return {"message": "Aucun créneau commun trouvé", "slots": []}

    hangout.confirmed_slot = common_slots[0]
    hangout.status = "confirmed"
    db.commit()

    return {
        "message": "Créneau trouvé et confirmé",
        "confirmed_slot": common_slots[0],
        "all_slots": common_slots,
    }
