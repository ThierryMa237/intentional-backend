from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import engine, Base, get_db
from app import models, schemas, auth
from app.routes import hangouts

from sqlalchemy import text

Base.metadata.create_all(bind=engine)

# Rattrapage (idempotent) : les hangouts créés avant l'ajout de la table
# hangout_participants doivent avoir leur créateur comme participant.
with engine.begin() as conn:
    conn.execute(text("""
        INSERT INTO hangout_participants (id, hangout_id, user_id, joined_at)
        SELECT gen_random_uuid(), h.id, h.creator_id, h.created_at
        FROM hangouts h
        WHERE NOT EXISTS (
            SELECT 1 FROM hangout_participants p
            WHERE p.hangout_id = h.id AND p.user_id = h.creator_id
        )
    """))

from fastapi.security import HTTPBearer
from fastapi.openapi.utils import get_openapi

app = FastAPI(title="Intentional API", version="0.1.0")

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Intentional API",
        version="0.1.0",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    openapi_schema["security"] = [{"bearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Routes auth
@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(
        models.User.phone == user.phone
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone already registered")
    new_user = models.User(
        name=user.name,
        phone=user.phone,
        hashed_password=auth.hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(
        models.User.phone == user.phone
    ).first()
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth.create_access_token({"sub": str(db_user.id)})
    return {"access_token": token}

# Routes hangouts
app.include_router(hangouts.router)