from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.tax_brackets import router as tax_brackets_router
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    application = FastAPI(title="Tax Document MS", version="0.1.0")
    application.include_router(health_router)
    application.include_router(tax_brackets_router)
    return application


app = create_app()
