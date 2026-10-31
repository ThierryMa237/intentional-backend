from datetime import datetime, timedelta, timezone

CHLOE = "+33600000001"
JORDAN = "+33600000002"
MARIE = "+33600000003"


def future(days=7, hour=18):
    d = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0, tzinfo=None)
    return (d + timedelta(days=days)).replace(hour=hour)


def create_diner(client, headers, **extra):
    payload = {
        "title": "Hangout diner",
        "hangout_type": "Diner",
        "place_name": "Salad & Co, Lille",
        "place_kind": "reservation",
        "message": "Ça faisait longtemps !",
        "start_at": future(hour=17).isoformat(),
        "end_at": future(hour=22).isoformat(),
        "invitee_phones": [JORDAN, "+33699999999"],
        **extra,
    }
    r = client.post("/hangouts/", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_cors_preflight(client):
    r = client.options("/hangouts/", headers={
        "Origin": "https://front.example", "Access-Control-Request-Method": "POST"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] in ("*", "https://front.example")


def test_creation_avec_invites(client, make_user):
    chloe = make_user("Chloé", CHLOE)
    make_user("Jordan", JORDAN)
    h = create_diner(client, chloe)
    assert h["hangout_type"] == "Diner"
    assert h["direction"] == "sent"
    assert h["my_status"] == "accepted"
    assert h["participant_count"] == 2
    assert h["invitees_status"] == "pending"
    assert h["not_registered"] == ["+33699999999"]


def test_type_invalide_refuse(client, make_user):
    chloe = make_user("Chloé", CHLOE)
    r = client.post("/hangouts/", json={"title": "x", "hangout_type": "Bowling"}, headers=chloe)
    assert r.status_code == 422


def test_recu_envoye_et_filtres(client, make_user):
    chloe = make_user("Chloé", CHLOE)
    jordan = make_user("Jordan", JORDAN)
    h = create_diner(client, chloe)

    recus = client.get("/hangouts/?direction=received", headers=jordan).json()
    assert [x["id"] for x in recus] == [h["id"]]
    assert recus[0]["my_status"] == "pending"
    assert client.get("/hangouts/?direction=sent", headers=jordan).json() == []

    r = client.post(f"/hangouts/{h['id']}/respond", json={"response": "declined"}, headers=jordan)
    assert r.json()["my_status"] == "declined"
    assert len(client.get("/hangouts/?direction=received&status=declined", headers=jordan).json()) == 1
    assert client.get("/hangouts/?direction=received&status=accepted", headers=jordan).json() == []

    envoyes = client.get("/hangouts/?direction=sent&status=declined", headers=chloe).json()
    assert envoyes[0]["invitees_status"] == "declined"


def test_non_membre_ne_voit_rien(client, make_user):
    chloe = make_user("Chloé", CHLOE)
    make_user("Jordan", JORDAN)
    marie = make_user("Marie", MARIE)
    h = create_diner(client, chloe)
    assert client.get(f"/hangouts/{h['id']}", headers=marie).status_code == 404
    r = client.post(f"/hangouts/{h['id']}/respond", json={"response": "accepted"}, headers=marie)
    assert r.status_code == 404


def test_parcours_complet_jusqu_au_match(client, make_user):
    chloe = make_user("Chloé", CHLOE)
    jordan = make_user("Jordan", JORDAN)
    h = create_diner(client, chloe)
    hid = h["id"]

    # Pas de dispo avant d'avoir accepté
    slot = {"slot_start": future(hour=18).isoformat(), "slot_end": future(hour=21).isoformat()}
    assert client.post(f"/hangouts/{hid}/availabilities", json=slot, headers=jordan).status_code == 409

    # Match impossible tant que Jordan n'a pas accepté
    assert client.post(f"/hangouts/{hid}/match", headers=chloe).status_code == 400

    client.post(f"/hangouts/{hid}/respond", json={"response": "accepted"}, headers=jordan)
    assert client.post(f"/hangouts/{hid}/availabilities", json=slot, headers=jordan).status_code == 201
    chloe_slot = {"slot_start": future(hour=16).isoformat(), "slot_end": future(hour=20).isoformat()}
    assert client.post(f"/hangouts/{hid}/availabilities", json=chloe_slot, headers=chloe).status_code == 201

    # Seul le créateur lance le match
    assert client.post(f"/hangouts/{hid}/match", headers=jordan).status_code == 403

    r = client.post(f"/hangouts/{hid}/match", headers=chloe)
    assert r.status_code == 200, r.text
    # Commun : 18h-20h ; fenêtre du hangout 17h-22h → premier créneau 18h
    assert r.json()["confirmed_slot"].startswith(future(hour=18).isoformat()[:16])

    detail = client.get(f"/hangouts/{hid}", headers=jordan).json()
    assert detail["status"] == "confirmed"
    # Plus de changement de réponse après confirmation
    r = client.post(f"/hangouts/{hid}/respond", json={"response": "declined"}, headers=jordan)
    assert r.status_code == 409


def test_fenetre_du_hangout_limite_le_match(client, make_user):
    chloe = make_user("Chloé", CHLOE)
    jordan = make_user("Jordan", JORDAN)
    h = create_diner(client, chloe, start_at=future(hour=20).isoformat(),
                     end_at=future(hour=22).isoformat())
    hid = h["id"]
    client.post(f"/hangouts/{hid}/respond", json={"response": "accepted"}, headers=jordan)
    wide = {"slot_start": future(hour=10).isoformat(), "slot_end": future(hour=23).isoformat()}
    client.post(f"/hangouts/{hid}/availabilities", json=wide, headers=jordan)
    client.post(f"/hangouts/{hid}/availabilities", json=wide, headers=chloe)
    slots = client.post(f"/hangouts/{hid}/match", headers=chloe).json()["all_slots"]
    assert slots[0].startswith(future(hour=20).isoformat()[:16])
    assert slots[-1].startswith(future(hour=21).isoformat()[:16])


def test_annulation(client, make_user):
    chloe = make_user("Chloé", CHLOE)
    jordan = make_user("Jordan", JORDAN)
    h = create_diner(client, chloe)
    assert client.post(f"/hangouts/{h['id']}/cancel", headers=jordan).status_code == 403
    r = client.post(f"/hangouts/{h['id']}/cancel", headers=chloe)
    assert r.json()["status"] == "cancelled"


def test_me(client, make_user):
    chloe = make_user("Chloé", CHLOE)
    assert client.get("/me", headers=chloe).json()["name"] == "Chloé"
