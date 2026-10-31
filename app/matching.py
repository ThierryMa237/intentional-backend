from datetime import datetime, timedelta
from typing import Dict, List, Tuple

Interval = Tuple[datetime, datetime]

SLOT_STEP_MINUTES = 30


def _merge(intervals: List[Interval]) -> List[Interval]:
    """Fusionne les intervalles qui se chevauchent ou se touchent."""
    merged: List[Interval] = []
    for start, end in sorted(i for i in intervals if i[0] < i[1]):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _intersect(a: List[Interval], b: List[Interval]) -> List[Interval]:
    """Intersection de deux listes d'intervalles triées et fusionnées."""
    result: List[Interval] = []
    i = j = 0
    while i < len(a) and j < len(b):
        start = max(a[i][0], b[j][0])
        end = min(a[i][1], b[j][1])
        if start < end:
            result.append((start, end))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return result


def _ceil_to_step(dt: datetime, step_minutes: int) -> datetime:
    """Arrondit à la prochaine heure 'ronde' (:00, :30 pour un pas de 30 min)."""
    base = dt.replace(second=0, microsecond=0)
    if base < dt:
        base += timedelta(minutes=1)
    remainder = base.minute % step_minutes
    if remainder:
        base += timedelta(minutes=step_minutes - remainder)
    return base


def find_common_slots(
    availabilities: Dict[str, List[Interval]],
    duration_minutes: int = 60,
    step_minutes: int = SLOT_STEP_MINUTES,
) -> List[datetime]:
    """
    Trouve les heures de début communes à tous les participants, alignées
    sur une grille fixe (:00 / :30), où chaque créneau dure au moins
    `duration_minutes`.

    availabilities = {
        "user_1": [(debut, fin), (debut, fin), ...],
        "user_2": [(debut, fin), ...],
    }
    """
    if not availabilities:
        return []

    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=step_minutes)

    # 1. Intersection des intervalles de tous les participants
    users = iter(availabilities.values())
    common = _merge(next(users))
    for ranges in users:
        common = _intersect(common, _merge(ranges))
        if not common:
            return []

    # 2. Découpage en heures de début alignées sur la grille
    slots: List[datetime] = []
    for start, end in common:
        current = _ceil_to_step(start, step_minutes)
        while current + duration <= end:
            slots.append(current)
            current += step
    return slots
