import logging

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from api.routers.public import squadlogs_routes
from services.config import BASE_DIR, settings
from services.schema_migrator import apply_migrations

# Set up logging so it appears in the terminal
logging.basicConfig(level=logging.INFO)

router = APIRouter()

app = FastAPI()
app.mount(
    "/static", StaticFiles(directory=BASE_DIR / "api" / "static"), name="static"
)

# Include routers here:
# E.g. app.include_router(auth.router)

app.include_router(squadlogs_routes.router)


def run_fastAPI():
    uvicorn.run(app, host="0.0.0.0", port=settings.WEB_PORT)

#1. Startup
def initialize_app():
    apply_migrations(settings.PROD_DB_PATH)
    # FastAPI is run on the main thread to ensure efficient operation.
    run_fastAPI()
    logging.info("Startup tasks finished.")

if __name__ == "__main__":
    try:
       initialize_app()
    except KeyboardInterrupt:
        print("Shutting down...")
