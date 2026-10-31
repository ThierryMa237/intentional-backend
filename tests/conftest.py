import os

# Variables d'env de test, AVANT d'importer l'app
os.environ.setdefault("SECRET_KEY", "test-secret-key-uniquement-pour-les-tests-0123456789")
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture()
def make_user(client):
    """Crée un compte et renvoie les headers d'auth."""
    def _make(name: str, phone: str):
        r = client.post("/register", json={"name": name, "phone": phone, "password": "motdepasse1"})
        assert r.status_code == 200, r.text
        r = client.post("/login", json={"phone": phone, "password": "motdepasse1"})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return _make
