# Documentation Technique — Intentional Backend

> Rédigée par : Thierry Manuel Zibiondobo  
> Date : Juin 2026  
> Projet : Intentional — Application mobile de coordination sociale entre amis

---

## Table des matières

1. [Vue d'ensemble du projet](#1-vue-densemble-du-projet)
2. [Stack technique](#2-stack-technique)
3. [Prérequis système](#3-prérequis-système)
4. [Installation pas à pas](#4-installation-pas-à-pas)
5. [Structure du projet](#5-structure-du-projet)
6. [Variables d'environnement](#6-variables-denvironnement)
7. [Lancer le projet en local](#7-lancer-le-projet-en-local)
8. [Endpoints disponibles](#8-endpoints-disponibles)
9. [Base de données](#9-base-de-données)
10. [Difficultés rencontrées et solutions](#10-difficultés-rencontrées-et-solutions)
11. [Prochaines étapes](#11-prochaines-étapes)

---

## 1. Vue d'ensemble du projet

**Intentional** est une application mobile sociale dont l'objectif est d'aider les adultes à organiser des rencontres réelles avec leurs amis (appelées "hangouts"). Ce dépôt contient le **backend** de l'application : une API REST construite avec FastAPI et connectée à une base de données PostgreSQL.

### Fonctionnalités développées à ce stade

| Fonctionnalité | Statut |
|---|---|
| Inscription utilisateur (`/register`) | ✅ Fonctionnel |
| Connexion utilisateur (`/login`) | ✅ Fonctionnel |
| Modèle de données : `users` | ✅ Table créée |
| Modèle de données : `hangouts` | ✅ Table créée |
| Modèle de données : `availabilities` | ✅ Table créée |
| Algorithme de matching de créneaux | ✅ Fonctionnel (testé) |
| Endpoint de santé (`/health`) | ✅ Fonctionnel |

---

## 2. Stack technique

| Composant | Technologie | Version |
|---|---|---|
| Langage | Python | 3.13 |
| Framework API | FastAPI | 0.137.x |
| Serveur ASGI | Uvicorn | latest |
| ORM | SQLAlchemy | latest |
| Base de données | PostgreSQL | 16 (via Docker) |
| Hachage de mots de passe | Passlib + Argon2 | latest |
| Authentification | JWT via python-jose | latest |
| Gestion des variables d'env | python-dotenv | latest |
| Conteneurisation | Docker Desktop | latest |
| Gestionnaire de paquets | pip (dans venv) | — |

---

## 3. Prérequis système

> Environnement de développement : **MacBook (macOS), architecture ARM (Apple Silicon)**

Installer dans cet ordre :

### 3.1 Homebrew
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 3.2 Python 3.12+
```bash
brew install python@3.12
```

### 3.3 Git
```bash
brew install git
git config --global user.name "Ton Nom"
git config --global user.email "ton@email.com"
```

### 3.4 Docker Desktop
```bash
brew install --cask docker
```
> ⚠️ Ouvrir l'application Docker depuis le Launchpad après installation pour qu'elle s'initialise.

### 3.5 Node.js (pour la future partie React Native)
```bash
brew install node
```

### 3.6 Visual Studio Code
```bash
brew install --cask visual-studio-code
```

---

## 4. Installation pas à pas

### 4.1 Cloner le dépôt
```bash
git clone git@github.com:ThierryMa237/intentional-backend.git
cd intentional-backend
```

### 4.2 Créer et activer l'environnement virtuel Python
```bash
python3 -m venv venv
source venv/bin/activate
```
> Le prompt doit afficher `(venv)` pour confirmer que l'environnement est actif.

### 4.3 Installer les dépendances Python
```bash
python3 -m pip install --upgrade pip
python3 -m pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv
python3 -m pip install "passlib[bcrypt]" argon2-cffi python-multipart
python3 -m pip install "python-jose[cryptography]"
```

> ⚠️ Sur macOS avec zsh, les crochets `[ ]` doivent être entourés de guillemets doubles
> (ex: `"passlib[bcrypt]"`) sinon zsh retourne `no matches found`.

### 4.4 Créer le fichier `.env`
```bash
cat > .env << 'EOF'
DATABASE_URL=postgresql://postgres:secret@localhost:5432/intentional
SECRET_KEY=un-secret-aleatoire-a-changer-en-production
EOF
```

### 4.5 Lancer la base de données PostgreSQL via Docker
```bash
docker run --name intentional-db \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=intentional \
  -p 5432:5432 \
  -d postgres
```

> La prochaine fois que tu relances le projet (après avoir éteint le Mac),
> utilise simplement `docker start intentional-db`.

---

## 5. Structure du projet

```
intentional-backend/
│
├── app/
│   ├── __init__.py          # Déclare app/ comme un package Python
│   ├── main.py              # Point d'entrée FastAPI, routes principales
│   ├── database.py          # Connexion SQLAlchemy à PostgreSQL
│   ├── models.py            # Modèles de données (tables SQL)
│   ├── schemas.py           # Schémas Pydantic (validation entrées/sorties)
│   ├── auth.py              # Logique d'authentification (hash, JWT)
│   └── matching.py          # Algorithme de matching de créneaux communs
│
├── tests/
│   ├── __init__.py
│   └── test_matching.py     # Test unitaire de l'algorithme de matching
│
├── .env                     # Variables d'environnement (non versionné)
├── .gitignore               # Fichiers ignorés par Git
├── requirements.txt         # Liste des dépendances Python
└── README.md                # Description générale du projet
```

---

## 6. Variables d'environnement

Le fichier `.env` doit être créé manuellement à la racine du projet (il n'est pas versionné sur Git pour des raisons de sécurité).

| Variable | Description | Exemple |
|---|---|---|
| `DATABASE_URL` | URL de connexion PostgreSQL | `postgresql://postgres:secret@localhost:5432/intentional` |
| `SECRET_KEY` | Clé secrète pour signer les tokens JWT | `une-chaine-aleatoire-longue` |

> ⚠️ En production, `SECRET_KEY` doit être une chaîne aléatoire longue et complexe,
> jamais committée sur Git.

---

## 7. Lancer le projet en local

### 7.1 S'assurer que Docker tourne
Ouvrir Docker Desktop depuis le Launchpad, puis :
```bash
docker start intentional-db
docker ps  # Vérifier que intentional-db est "Up"
```

### 7.2 Activer l'environnement virtuel
```bash
cd intentional-backend
source venv/bin/activate
```

### 7.3 Lancer le serveur FastAPI
```bash
uvicorn app.main:app --reload
```

Le serveur est accessible sur : `http://127.0.0.1:8000`  
La documentation Swagger interactive : `http://127.0.0.1:8000/docs`

### 7.4 Tester l'algorithme de matching
```bash
python3 -m tests.test_matching
```

---

## 8. Endpoints disponibles

### GET `/health`
Vérifie que le serveur répond.
```json
{ "status": "ok" }
```

### POST `/register`
Crée un nouvel utilisateur.

**Body :**
```json
{
  "name": "Thierry",
  "phone": "0600000001",
  "password": "monmotdepasse"
}
```

**Réponse 200 :**
```json
{
  "id": "07f14b83-e002-4eef-ac49-313ea31b6fe9",
  "name": "Thierry",
  "phone": "0600000001",
  "created_at": "2026-06-22T07:33:12.775968"
}
```

### POST `/login`
Authentifie un utilisateur et retourne un token JWT.

**Body :**
```json
{
  "name": "Thierry",
  "phone": "0600000001",
  "password": "monmotdepasse"
}
```

**Réponse 200 :**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 9. Base de données

### Schéma des tables

```sql
-- Table des utilisateurs
CREATE TABLE users (
  id UUID PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  phone VARCHAR(20) UNIQUE NOT NULL,
  hashed_password VARCHAR(255) NOT NULL,
  created_at TIMESTAMP
);

-- Table des hangouts (rencontres)
CREATE TABLE hangouts (
  id UUID PRIMARY KEY,
  creator_id UUID REFERENCES users(id),
  title VARCHAR(200) NOT NULL,
  status VARCHAR(20) DEFAULT 'pending',
  confirmed_slot TIMESTAMP,
  created_at TIMESTAMP
);

-- Table des disponibilités (pour le matching)
CREATE TABLE availabilities (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  hangout_id UUID REFERENCES hangouts(id),
  slot_start TIMESTAMP NOT NULL,
  slot_end TIMESTAMP NOT NULL
);
```

### Se connecter directement à la base
```bash
docker exec -it intentional-db psql -U postgres -d intentional
```

Commandes utiles dans psql :
```sql
\dt          -- Lister les tables
\d users     -- Décrire la structure de la table users
SELECT * FROM users;  -- Voir les utilisateurs enregistrés
\q           -- Quitter
```

---

## 10. Difficultés rencontrées et solutions

### 🔴 Problème 1 — `ModuleNotFoundError: No module named 'fastapi'`
**Cause :** L'environnement virtuel n'était pas actif. Python utilisait
l'interpréteur système (`/usr/local/bin/python3`) au lieu de celui du venv.

**Solution :**
```bash
source venv/bin/activate
```
Vérifier que `(venv)` apparaît dans le prompt avant toute commande Python.

**Dans VS Code :** `Cmd+Shift+P` → "Python: Select Interpreter" → choisir
`./venv/bin/python3`.

---

### 🔴 Problème 2 — `git push` rejeté : "fetch first"
**Cause :** Le dépôt distant (GitHub) contenait des commits que le dépôt local
n'avait pas (README créé via l'interface GitHub).

**Solution :**
```bash
git pull origin main --rebase
# Résoudre les conflits si nécessaire
git push
```

---

### 🔴 Problème 3— Conflit de fusion dans `app/main.py`
**Cause :** Le `git pull --rebase` a détecté des modifications concurrentes
dans `main.py` entre la version locale et la version distante.

**Solution :** Ouvrir le fichier dans VS Code, supprimer tous les marqueurs
de conflit (`<<<<<<<`, `=======`, `>>>>>>>`), garder la version correcte,
puis :
```bash
git add app/main.py
git commit -m "Resolve merge conflict in main.py"
git push
```

---

### 🔴 Problème 4 — `HEAD détachée` (detached HEAD)
**Cause :** Un rebase interrompu a laissé Git dans un état où aucune branche
n'était active.

**Solution :**
```bash
git checkout main
git merge <hash-du-commit>  # ex: git merge 5ddd351
git push
```

---

### 🔴 Problème 5 — `sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL`
**Cause :** Le fichier `.env` était absent ou mal placé (pas à la racine du
projet), donc `DATABASE_URL` retournait `None`.

**Solution :** Vérifier l'emplacement du `.env` :
```bash
ls -la  # Le .env doit être au même niveau que le dossier app/
cat .env  # Vérifier le contenu
```
Recréer si nécessaire :
```bash
cat > .env << 'EOF'
DATABASE_URL=postgresql://postgres:secret@localhost:5432/intentional
EOF
```

---

### 🔴 Problème 6 — `Did not find any tables` dans PostgreSQL
**Cause :** La ligne `Base.metadata.create_all(bind=engine)` dans `main.py`
ne créait pas les tables car `from app import models` était absent.
Sans cet import, SQLAlchemy ne "voit" pas les classes `User`, `Hangout`, etc.

**Solution :** S'assurer que `main.py` contient :
```python
from app import models  # ← indispensable
Base.metadata.create_all(bind=engine)
```

---

### 🔴 Problème 7— `zsh: no matches found: passlib[bcrypt]`
**Cause :** Le shell zsh (macOS) interprète les crochets `[ ]` comme des
patterns de fichiers (glob), pas comme du texte littéral.

**Solution :** Entourer le nom du paquet de guillemets doubles :
```bash
python3 -m pip install "passlib[bcrypt]" "python-jose[cryptography]"
```

---

### 🔴 Problème 8 — `passlib.exc.MissingBackendError: bcrypt: no backends available`
**Cause :** Incompatibilité entre `passlib` et les versions récentes de
`bcrypt` (4.x) sur Python 3.13. passlib ne détecte pas automatiquement le
backend bcrypt installé.

**Solution :** Remplacer bcrypt par **argon2** (plus moderne, mieux supporté) :
```bash
python3 -m pip install argon2-cffi
```
Dans `app/auth.py` :
```python
# Remplacer :
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Par :
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
```

---

### 🟡 Problème 9 — `uvicorn: command not found`
**Cause :** L'environnement virtuel n'était pas actif dans le terminal courant.
uvicorn est installé dans le venv, pas dans le système.

**Solution :**
```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

---

### 🟡 Problème 10 — `Address already in use` (port 8000)
**Cause :** Un processus uvicorn précédent tournait toujours en arrière-plan.

**Solution :**
```bash
lsof -ti:8000 | xargs kill -9
uvicorn app.main:app --reload
```

---

## 11. Prochaines étapes

Les fonctionnalités à développer, dans l'ordre recommandé :

1. **Endpoints CRUD Hangouts** — créer, lire, modifier, annuler un hangout
2. **Endpoint Availabilities** — ajouter ses disponibilités à un hangout
3. **Endpoint Matching** — déclencher l'algorithme et confirmer un créneau
4. **Middleware d'authentification** — protéger les routes avec le token JWT
5. **WebSockets** — partage de localisation en temps réel (Hangout improvisé)
6. **Intégration Google Calendar API** — import automatique des disponibilités
7. **Notifications push** — via Firebase Cloud Messaging
8. **Déploiement** — Railway.app ou Render pour exposer l'API publiquement
9. **Frontend React Native** — interface mobile iOS/Android avec Expo

---

*Document maintenu par l'équipe technique du projet Intentional.*
*Pour toute question : ouvrir une issue sur le dépôt GitHub.*
