# Intentional — Backend

API de l'app **Intentional** (organiser des hangouts intentionnels entre ami·es).
La référence fonctionnelle est la maquette [JxC-Lab/Intentional](https://github.com/JxC-Lab/Intentional).

- **Prod** : https://intentional-backend-1.onrender.com — documentation interactive sur [`/docs`](https://intentional-backend-1.onrender.com/docs)
- Stack : FastAPI · SQLAlchemy 2 · PostgreSQL · Alembic · JWT

> L'offre gratuite de Render met le service en veille après 15 min sans requête :
> le premier appel peut prendre 30 à 60 s.

## Pour l'équipe front

Authentification : `POST /login` renvoie `access_token`, à envoyer ensuite dans le header
`Authorization: Bearer <token>`. Les dates sont en ISO 8601 ; elles sont stockées et renvoyées en **UTC**.

| Écran de la maquette | Route |
|---|---|
| Inscription / connexion | `POST /register` · `POST /login` · `GET /me` |
| Nouveau hangout | `POST /hangouts/` (invité·es via `invitee_phones`) |
| Mes hangouts (Reçu / Envoyé, Tous / Accepté / Refusé) | `GET /hangouts/?direction=received\|sent\|all&status=all\|pending\|accepted\|declined` |
| Détail hangout | `GET /hangouts/{id}` |
| Invitation reçue : Accepter / Indisponible | `POST /hangouts/{id}/respond` `{"response": "accepted" \| "declined"}` |
| Ajouter un·e invité·e | `POST /hangouts/{id}/participants` `{"phone": "+33…"}` |
| Mes disponibilités | `POST /hangouts/{id}/availabilities` |
| Créneau commun trouvé | `POST /hangouts/{id}/match?duration_minutes=60` |
| Annuler | `POST /hangouts/{id}/cancel` |

Valeurs autorisées :

- `hangout_type` : `Diner`, `Café`, `Cinéma`, `Sport`, `Journaling`, `Administratif`, `Co-working`, `Sunday Brunch`
- `mode` : `planned` (Planifié) · `spontaneous` (Improvisé)
- `place_kind` : `reservation` · `free`
- statut d'un hangout : `pending` · `confirmed` · `cancelled`
- réponse d'un·e participant·e : `pending` · `accepted` · `declined` (Indisponible)

Chaque hangout renvoyé contient `direction` (`sent`/`received`), `my_status` (ma réponse) et,
pour un hangout envoyé, `invitees_status` (réponses agrégées des invité·es).
À la création, `not_registered` liste les numéros qui n'ont pas encore de compte.

Règles : seul·e le·la créateur·rice invite, lance le matching ou annule ; il faut avoir accepté
pour donner ses disponibilités ; le matching ne tient compte que des personnes ayant accepté et
reste dans la fenêtre `start_at` / `end_at` du hangout.

## Lancer en local

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
docker compose up -d db          # PostgreSQL local
alembic upgrade head             # crée / met à jour les tables
uvicorn app.main:app --reload    # http://localhost:8000/docs
pytest                           # tests (SQLite en mémoire, pas besoin de Postgres)
```

Le fichier `.env` (non commité) doit contenir `DATABASE_URL` et `SECRET_KEY` (32 caractères minimum).

## Variables d'environnement

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | URL PostgreSQL (Neon en prod, avec `?sslmode=require`) |
| `SECRET_KEY` | Clé de signature des JWT, ≥ 32 caractères — obligatoire |
| `CORS_ORIGINS` | Origines du front autorisées, séparées par des virgules (défaut `*`) |

## Modifier la base

Ne jamais modifier les tables à la main : changer `app/models.py`, puis

```bash
alembic revision --autogenerate -m "description du changement"
# relire le fichier créé dans migrations/versions/, puis :
alembic upgrade head
```

En prod, `alembic upgrade head` est lancé automatiquement au démarrage du conteneur.
