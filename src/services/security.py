from passlib.context import CryptContext
from fastapi import Request, Cookie, status, Depends, HTTPException, Security
from fastapi.responses import RedirectResponse, Response
from services.db_connection import get_db_context
from datetime import datetime, timezone
import logging 
from fastapi.security import APIKeyHeader
from services.config import settings
from typing import Annotated, Optional

logger = logging.getLogger("auth")
logging.basicConfig(level=logging.INFO)

auth_header_scheme = APIKeyHeader(name="Authorization", auto_error=False)

async def verify_api_code_and_log(
    request: Request, 
    auth_header: str = Security(auth_header_scheme)
) -> str:
    # 1. Log the incoming request
    client_ip = request.client.host if request.client else "Unknown IP"
    logger.info(f"Incoming API Request: {request.method} {request.url.path} | Source: {client_ip}")

    # 2. Check if the header was provided at all
    if not auth_header:
        logger.warning(f"Rejected: Missing Authorization header | Source: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing",
        )

    # 3. Clean the token (handles both "Bearer <code\>" and just "<code\>")
    provided_code = auth_header.replace("Bearer ", "").strip()
    expected_code = settings.API_SECRET_CODE

    # 4. Verify the code
    if provided_code != expected_code:
        logger.warning(f"Rejected: Invalid authorization code | Source: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization code",
        )

    logger.info(f"Accepted: Valid API authorization | Source: {client_ip}")
    return provided_code
