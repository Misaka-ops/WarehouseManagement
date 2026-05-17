from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import SessionLocal
from .routers import inventory, purchases
from .services.bootstrap import create_schema, seed_data


settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inventory.router, prefix=settings.api_prefix)
app.include_router(purchases.router, prefix=settings.api_prefix)


@app.on_event("startup")
def startup():
    create_schema()
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()


@app.get("/health")
def healthcheck():
    return {"status": "ok"}

