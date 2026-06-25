from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.auth import get_current_user
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid

router = APIRouter(prefix="/hangouts", tags=["hangouts"])

# Schémas
class HangoutCreate(BaseModel):
    title: str

class HangoutOut(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    created_at: datetime
    confirmed_slot: Optional[datetime] = None

    class Config:
        from_attributes = True

class AvailabilityCreate(BaseModel):
    slot_start: datetime
    slot_end: datetime


# Créer un hangout
@router.post("/", response_model=HangoutOut)
def create_hangout(
    hangout: HangoutCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    new_hangout = models.Hangout(
        title=hangout.title,
        creator_id=current_user.id
    )
    db.add(new_hangout)
    db.commit()
    db.refresh(new_hangout)
    return new_hangout


# Lister ses hangouts
@router.get("/", response_model=list[HangoutOut])
def list_hangouts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.Hangout).filter(
        models.Hangout.creator_id == current_user.id
    ).all()


# Ajouter ses disponibilités à un hangout
@router.post("/{hangout_id}/availabilities")
def add_availability(
    hangout_id: uuid.UUID,
    availability: AvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    hangout = db.query(models.Hangout).filter(
        models.Hangout.id == hangout_id
    ).first()
    if not hangout:
        raise HTTPException(status_code=404, detail="Hangout introuvable")

    new_avail = models.Availability(
        user_id=current_user.id,
        hangout_id=hangout_id,
        slot_start=availability.slot_start,
        slot_end=availability.slot_end
    )
    db.add(new_avail)
    db.commit()
    return {"message": "Disponibilité ajoutée"}


# Déclencher le matching
@router.post("/{hangout_id}/match")
def match_hangout(
    hangout_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    from app.matching import find_common_slots

    availabilities_db = db.query(models.Availability).filter(
        models.Availability.hangout_id == hangout_id
    ).all()

    if not availabilities_db:
        raise HTTPException(status_code=400, detail="Aucune disponibilité enregistrée")

    # Regrouper par utilisateur
    avail_dict = {}
    for a in availabilities_db:
        uid = str(a.user_id)
        if uid not in avail_dict:
            avail_dict[uid] = []
        avail_dict[uid].append((a.slot_start, a.slot_end))

    common_slots = find_common_slots(avail_dict)

    if not common_slots:
        return {"message": "Aucun créneau commun trouvé", "slots": []}

    # Confirmer le premier créneau commun
    hangout = db.query(models.Hangout).filter(
        models.Hangout.id == hangout_id
    ).first()
    hangout.confirmed_slot = common_slots[0]
    hangout.status = "confirmed"
    db.commit()

    return {
        "message": "Créneau trouvé et confirmé",
        "confirmed_slot": common_slots[0],
        "all_slots": common_slots
    }