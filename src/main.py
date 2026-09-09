# 
from fastapi import FastAPI, HTTPException, status, Request, Form, Header, Depends, APIRouter
from dotenv import load_dotenv
import logging
import os
from pydantic import BaseModel
from api.routers.private import dashboard
from services.config import settings
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uvicorn
from api.routers.public import login_routes, public_routes, squadlogs_routes
from starlette.middleware.sessions import SessionMiddleware
from services.schema_migrator import apply_migrations
from services.security import web_login_required
from database.db_authentication import fetch_user_session, count_total_users
from services.db_connection import get_db, get_db_context
from contextlib import asynccontextmanager

# Set up logging so it appears in the terminal
logging.basicConfig(level=logging.INFO)

# Create and load environment variables
BASE_DIR = Path(__file__).resolve().parent

# This should output somepath/src
logging.info(f"Base path set to: {BASE_DIR}")

router = APIRouter()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP LOGIC ---
    # Check if the database is empty on boot
    with get_db_context() as db:
        total_users = count_total_users(db) 
    
    # Store the setup state globally in app.state
    app.state.needs_setup = (total_users == 0)
    
    if app.state.needs_setup:
        logging.info("No users found. Initial setup route activated.")
        
    yield
    
    print("Shutting down.")

app = FastAPI(lifespan=lifespan)
app.mount(
    "/static", StaticFiles(directory=BASE_DIR / "api" / "static"), name="static"
)

# Include routers here:
# E.g. app.include_router(auth.router)
app.include_router(
    dashboard.router, 
    dependencies=[Depends(web_login_required)]
    )
app.include_router(login_routes.router)
app.include_router(public_routes.router)
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