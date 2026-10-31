from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from datetime import datetime, timezone
from typing import Literal, Optional
import re
import uuid

from app.database import get_db
from app import models
from app.auth import get_current_user
from app.matching import find_common_slots
from app.schemas import PHONE_PATTERN

router = APIRouter(prefix="/hangouts", tags=["hangouts"])

MAX_INVITEES = 20


# ---------- Helpers de dates ----------

def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Les colonnes DateTime sont sans fuseau : on stocke tout en UTC naïf."""
    if dt is not None and dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


# ---------- Schémas d'entrée ----------

class HangoutCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    hangout_type: Optional[Literal[models.HANGOUT_TYPES]] = None
    mode: Literal[models.HANGOUT_MODES] = "planned"
    place_name: Optional[str] = Field(default=None, max_length=200)
    place_kind: Optional[Literal[models.PLACE_KINDS]] = None
    description: Optional[str] = Field(default=None, max_length=2000)
    image_url: Optional[str] = Field(default=None, max_length=500, pattern=r"^https?://")
    message: Optional[str] = Field(default=None, max_length=280)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    invitee_phones: list[str] = Field(default_factory=list, max_length=MAX_INVITEES)

    @field_validator("start_at", "end_at")
    @classmethod
    def normalize_tz(cls, v):
        return _to_naive_utc(v)

    @field_validator("invitee_phones")
    @classmethod
    def check_phones(cls, phones: list[str]) -> list[str]:
        for p in phones:
            if not re.fullmatch(PHONE_PATTERN, p):
                raise ValueError(f"Numéro invalide : {p}")
        return list(dict.fromkeys(phones))  # dédoublonne en gardant l'ordre

    @model_validator(mode="after")
    def check_window(self):
        if self.start_at and self.end_at and self.end_at <= self.start_at:
            raise ValueError("end_at doit être après start_at")
        if self.end_at and self.end_at <= models.utcnow():
            raise ValueError("La fin du hangout est déjà passée")
        return self


class ParticipantAdd(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN)


class InvitationResponse(BaseModel):
    response: Literal["accepted", "declined"]


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


# ---------- Schémas de sortie ----------

class UserBrief(BaseModel):
    id: uuid.UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class ParticipantOut(BaseModel):
    user: UserBrief
    status: str
    responded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class HangoutOut(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    hangout_type: Optional[str] = None
    mode: str
    place_name: Optional[str] = None
    place_kind: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    message: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    confirmed_slot: Optional[datetime] = None
    created_at: datetime
    creator: UserBrief
    participants: list[ParticipantOut]
    participant_count: int
    # Point de vue de l'utilisateur connecté (onglets Reçu / Envoyé de la maquette)
    direction: Literal["sent", "received"]
    my_status: str
    # Pour un hangout envoyé : où en sont les réponses des invité·es
    invitees_status: Optional[str] = None


class HangoutCreated(HangoutOut):
    # Numéros sans compte Intentional (pour l'invitation par SMS, plus tard)
    not_registered: list[str] = []


# ---------- Helpers métier ----------

def _invitees_status(hangout: models.Hangout) -> Optional[str]:
    """Agrège les réponses des invité·es (tout le monde sauf le créateur)."""
    statuses = [p.status for p in hangout.participants if p.user_id != hangout.creator_id]
    if not statuses:
        return None
    if "pending" in statuses:
        return "pending"
    if "accepted" in statuses:
        return "accepted"
    return "declined"


def _to_out(hangout: models.Hangout, me: models.User) -> dict:
    mine = next((p for p in hangout.participants if p.user_id == me.id), None)
    sent = hangout.creator_id == me.id
    return {
        **{c: getattr(hangout, c) for c in (
            "id", "title", "status", "hangout_type", "mode", "place_name", "place_kind",
            "description", "image_url", "message", "start_at", "end_at",
            "confirmed_slot", "created_at",
        )},
        "creator": hangout.creator,
        "participants": hangout.participants,
        "participant_count": len(hangout.participants),
        "direction": "sent" if sent else "received",
        "my_status": mine.status if mine else "pending",
        "invitees_status": _invitees_status(hangout) if sent else None,
    }


def _load_hangout(db: Session, hangout_id: uuid.UUID) -> Optional[models.Hangout]:
    return (
        db.query(models.Hangout)
        .options(
            selectinload(models.Hangout.participants).selectinload(models.HangoutParticipant.user),
            selectinload(models.Hangout.creator),
        )
        .filter(models.Hangout.id == hangout_id)
        .first()
    )


def _get_my_hangout(db: Session, hangout_id: uuid.UUID, user: models.User):
    """Renvoie (hangout, ma ligne participant). 404 si absent ou si je n'en fais pas partie
    (on ne révèle pas l'existence d'un hangout aux non-membres)."""
    hangout = _load_hangout(db, hangout_id)
    mine = None
    if hangout:
        mine = next((p for p in hangout.participants if p.user_id == user.id), None)
    if not hangout or not mine:
        raise HTTPException(status_code=404, detail="Hangout introuvable")
    return hangout, mine


def _require_creator(hangout: models.Hangout, user: models.User) -> None:
    if hangout.creator_id != user.id:
        raise HTTPException(status_code=403, detail="Seul le créateur peut faire cette action")


def _require_pending(hangout: models.Hangout) -> None:
    if hangout.status != "pending":
        raise HTTPException(
            status_code=409, detail=f"Hangout déjà {hangout.status}, action impossible"
        )


# ---------- Routes ----------

@router.post("/", response_model=HangoutCreated, status_code=201)
def create_hangout(
    payload: HangoutCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Écran « Nouveau hangout ». Les invité·es peuvent être ajouté·es dès la création
    via `invitee_phones` ; les numéros sans compte sont renvoyés dans `not_registered`."""
    now = models.utcnow()
    data = payload.model_dump(exclude={"invitee_phones"})
    hangout = models.Hangout(**data, creator_id=current_user.id, status="pending")
    # Le créateur participe d'office et a « accepté »
    hangout.participants.append(models.HangoutParticipant(
        user_id=current_user.id, status="accepted", responded_at=now
    ))

    not_registered = []
    if payload.invitee_phones:
        users = db.query(models.User).filter(models.User.phone.in_(payload.invitee_phones)).all()
        by_phone = {u.phone: u for u in users}
        for phone in payload.invitee_phones:
            user = by_phone.get(phone)
            if user is None:
                not_registered.append(phone)
            elif user.id != current_user.id:
                hangout.participants.append(models.HangoutParticipant(user_id=user.id))

    db.add(hangout)
    db.commit()
    hangout = _load_hangout(db, hangout.id)
    return {**_to_out(hangout, current_user), "not_registered": not_registered}


@router.get("/", response_model=list[HangoutOut])
def list_hangouts(
    direction: Literal["all", "received", "sent"] = Query(
        "all", description="Onglets Reçu / Envoyé"),
    status: Literal["all", "pending", "accepted", "declined"] = Query(
        "all", description="Filtre Tous / Accepté / Refusé (+ en attente)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Écran « Mes hangouts ». Pour un hangout reçu, `status` filtre sur MA réponse ;
    pour un hangout envoyé, sur la réponse agrégée des invité·es (`invitees_status`)."""
    hangouts = (
        db.query(models.Hangout)
        .join(models.HangoutParticipant)
        .filter(models.HangoutParticipant.user_id == current_user.id)
        .options(
            selectinload(models.Hangout.participants).selectinload(models.HangoutParticipant.user),
            selectinload(models.Hangout.creator),
        )
        .order_by(models.Hangout.created_at.desc())
        .all()
    )
    result = []
    for h in hangouts:
        out = _to_out(h, current_user)
        if direction != "all" and out["direction"] != direction:
            continue
        if status != "all":
            value = out["invitees_status"] if out["direction"] == "sent" else out["my_status"]
            if value != status:
                continue
        result.append(out)
    return result


@router.get("/{hangout_id}", response_model=HangoutOut)
def get_hangout(
    hangout_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Écran « Détail hangout »."""
    hangout, _ = _get_my_hangout(db, hangout_id, current_user)
    return _to_out(hangout, current_user)


@router.post("/{hangout_id}/participants", response_model=HangoutOut)
def add_participant(
    hangout_id: uuid.UUID,
    participant: ParticipantAdd,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Le créateur invite un·e utilisateur·rice inscrit·e via son numéro."""
    hangout, _ = _get_my_hangout(db, hangout_id, current_user)
    _require_creator(hangout, current_user)
    _require_pending(hangout)

    user = db.query(models.User).filter(models.User.phone == participant.phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="Aucun utilisateur avec ce numéro")
    if not any(p.user_id == user.id for p in hangout.participants):
        db.add(models.HangoutParticipant(hangout_id=hangout_id, user_id=user.id))
        db.commit()
        hangout = _load_hangout(db, hangout_id)
    return _to_out(hangout, current_user)


@router.post("/{hangout_id}/respond", response_model=HangoutOut)
def respond_to_invitation(
    hangout_id: uuid.UUID,
    payload: InvitationResponse,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Boutons « Accepter » / « Indisponible ». On peut changer d'avis tant que
    le hangout n'est pas confirmé."""
    hangout, mine = _get_my_hangout(db, hangout_id, current_user)
    if hangout.creator_id == current_user.id:
        raise HTTPException(status_code=400, detail="Le créateur n'a pas à répondre")
    _require_pending(hangout)

    mine.status = payload.response
    mine.responded_at = models.utcnow()
    db.commit()
    return _to_out(_load_hangout(db, hangout_id), current_user)


@router.post("/{hangout_id}/cancel", response_model=HangoutOut)
def cancel_hangout(
    hangout_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    hangout, _ = _get_my_hangout(db, hangout_id, current_user)
    _require_creator(hangout, current_user)
    if hangout.status == "cancelled":
        raise HTTPException(status_code=409, detail="Hangout déjà annulé")
    hangout.status = "cancelled"
    db.commit()
    return _to_out(_load_hangout(db, hangout_id), current_user)


@router.post("/{hangout_id}/availabilities", status_code=201)
def add_availability(
    hangout_id: uuid.UUID,
    availability: AvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Il faut avoir accepté l'invitation pour donner ses disponibilités."""
    hangout, mine = _get_my_hangout(db, hangout_id, current_user)
    _require_pending(hangout)
    if mine.status != "accepted":
        raise HTTPException(
            status_code=409, detail="Accepte d'abord l'invitation pour donner tes disponibilités"
        )

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
    duration_minutes: int = Query(60, ge=15, le=720),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """« Créneau commun trouvé ». Ne prend en compte que les participant·es qui ont
    accepté (le créateur compris) ; les invitations en attente sont ignorées.
    Si le hangout a une fenêtre Début/Fin, les créneaux y sont limités."""
    hangout, _ = _get_my_hangout(db, hangout_id, current_user)
    _require_creator(hangout, current_user)
    _require_pending(hangout)

    accepted = {p.user_id for p in hangout.participants if p.status == "accepted"}
    if len(accepted) < 2:
        raise HTTPException(
            status_code=400, detail="Il faut au moins 2 participant·es ayant accepté"
        )

    availabilities_db = db.query(models.Availability).filter(
        models.Availability.hangout_id == hangout_id
    ).all()
    avail_dict: dict = {}
    for a in availabilities_db:
        if a.user_id in accepted:
            avail_dict.setdefault(a.user_id, []).append((a.slot_start, a.slot_end))

    missing = accepted - set(avail_dict)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"{len(missing)} participant·e(s) n'ont pas encore donné leurs disponibilités",
        )

    # La fenêtre Début/Fin du hangout se comporte comme une contrainte de plus
    if hangout.start_at or hangout.end_at:
        window_start = hangout.start_at or datetime.min
        window_end = hangout.end_at or datetime.max
        avail_dict["__window__"] = [(window_start, window_end)]

    now = models.utcnow()
    common_slots = [s for s in find_common_slots(avail_dict, duration_minutes) if s >= now]

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
