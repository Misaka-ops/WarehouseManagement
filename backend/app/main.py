from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import auth, inventory, purchases, settings as settings_router
from .services.bootstrap import create_schema


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
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(settings_router.router, prefix=settings.api_prefix)


@app.on_event("startup")
def startup():
    create_schema()


@app.get("/health")
def healthcheck():
    return {"status": "ok"}
