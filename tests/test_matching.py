from datetime import datetime
from app.matching import find_common_slots

availabilities = {
    "alice": [(datetime(2025, 5, 25, 18, 0), datetime(2025, 5, 25, 22, 0))],
    "bob":   [(datetime(2025, 5, 25, 19, 0), datetime(2025, 5, 25, 23, 0))],
}

result = find_common_slots(availabilities, duration_minutes=60)
print("Créneaux communs trouvés :")
for slot in result:
    print(f" - {slot}")