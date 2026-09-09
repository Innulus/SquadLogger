from fastapi.responses import RedirectResponse, HTMLResponse, Response
from fastapi import APIRouter, Request, Form, HTTPException, status
import logging
from pathlib import Path
from fastapi.templating import Jinja2Templates
from services.config import settings, BASE_DIR


logger = logging.getLogger("logs")
logging.basicConfig(level=logging.INFO)

router = APIRouter()
templates = Jinja2Templates(directory=BASE_DIR / "api" / "templates")

