from datetime import datetime, timedelta
from typing import List, Tuple, Dict

def find_common_slots(
    availabilities: Dict[str, List[Tuple[datetime, datetime]]],
    duration_minutes: int = 60
) -> List[datetime]:
    """
    Trouve les créneaux de début communs à tous les participants,
    où chaque créneau dure au moins `duration_minutes`.
    
    availabilities = {
        "user_1": [(debut, fin), (debut, fin), ...],
        "user_2": [(debut, fin), ...],
    }
    """
    if not availabilities:
        return []

    step = timedelta(minutes=30)
    duration = timedelta(minutes=duration_minutes)

    # Étape 1 : transformer chaque dispo en un ensemble de créneaux de 30 min
    user_slot_sets = []
    for user_id, ranges in availabilities.items():
        slots = set()
        for start, end in ranges:
            current = start
            while current + duration <= end:
                slots.add(current)
                current += step
        user_slot_sets.append(slots)

    # Étape 2 : intersection de tous les ensembles
    common = user_slot_sets[0]
    for slots in user_slot_sets[1:]:
        common = common & slots

    return sorted(common)