from datetime import datetime
from app.matching import find_common_slots


def dt(h, m=0):
    return datetime(2025, 5, 25, h, m)


def test_overlap_simple():
    result = find_common_slots({
        "alice": [(dt(18), dt(22))],
        "bob": [(dt(19), dt(23))],
    }, duration_minutes=60)
    assert result == [dt(19), dt(19, 30), dt(20), dt(20, 30), dt(21)]


def test_heures_de_debut_non_alignees():
    # Ancien bug : 18h15 vs 18h00 ne donnait aucun créneau
    result = find_common_slots({
        "alice": [(dt(18, 15), dt(22))],
        "bob": [(dt(18), dt(23))],
    }, duration_minutes=60)
    assert result[0] == dt(18, 30)
    assert result[-1] == dt(21)


def test_aucun_chevauchement():
    assert find_common_slots({
        "alice": [(dt(10), dt(12))],
        "bob": [(dt(14), dt(16))],
    }) == []


def test_chevauchement_trop_court():
    assert find_common_slots({
        "alice": [(dt(10), dt(11))],
        "bob": [(dt(10, 30), dt(12))],
    }, duration_minutes=60) == []


def test_plages_adjacentes_fusionnees():
    # 18h-19h + 19h-20h = 18h-20h pour Alice
    result = find_common_slots({
        "alice": [(dt(18), dt(19)), (dt(19), dt(20))],
        "bob": [(dt(18, 30), dt(20))],
    }, duration_minutes=60)
    assert result == [dt(18, 30), dt(19)]


def test_trois_participants():
    result = find_common_slots({
        "a": [(dt(9), dt(18))],
        "b": [(dt(12), dt(15))],
        "c": [(dt(13), dt(20))],
    }, duration_minutes=90)
    assert result == [dt(13), dt(13, 30)]


def test_vide():
    assert find_common_slots({}) == []
