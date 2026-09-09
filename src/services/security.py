from passlib.context import CryptContext
from fastapi import Request, Cookie, status, Depends, HTTPException, Security
from fastapi.responses import RedirectResponse, Response
from database.db_authentication import fetch_user_session, revoke_user_session, fetch_user_permissions_by_id
from services.db_connection import get_db_context
from datetime import datetime, timezone
import logging 
from fastapi.security import APIKeyHeader
from services.config import settings
from typing import Annotated, Optional

logger = logging.getLogger("auth")
logging.basicConfig(level=logging.INFO)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

COOKIE_TTL = settings.COOKIE_TTL
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_session_token_from_request(request: Request) -> Optional[str]:
    return request.cookies.get("session_token")

def get_current_user_session(request: Request) -> Optional[dict]:
    # This function does not have any enforcement logic and simply checks and returns the status of a users session

    # Fetch session token from request cookies
    session_token = request.cookies.get("session_token")

    if not session_token:
        return None

    with get_db_context() as db:
        session_data = fetch_user_session(db, session_token)
        if not session_data:
            return None

        now = datetime.now(timezone.utc)
        date_issued = datetime.fromisoformat(session_data["created_at"]).replace(tzinfo=timezone.utc)
        is_revoked = session_data.get("is_active") == 0
        is_expired = (now - date_issued).total_seconds() >= COOKIE_TTL

        if is_revoked or is_expired:
            if is_expired:
                revoke_user_session(db, session_token)
            return None

        # Add permissions fetched from user table to session data
        
        session_data["permissions"] = fetch_user_permissions_by_id(db, session_data["user_id"])
        return session_data

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

# This is for API authorization requirements
async def api_login_required(
    user: Optional[dict] = Depends(get_current_user_session)
) -> dict:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    return user

# This is for web login requirements
async def web_login_required(
    request: Request,
    user: Optional[dict] = Depends(get_current_user_session)
) -> dict:
    if not user:
        redirect_url = "/login"
        
        # Support HTMX client-side redirects
        if request.headers.get("HX-Request"):
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                headers={"HX-Redirect": redirect_url},
            )
            
        # Standard browser redirect
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": redirect_url},
        )
    return user
    
async def admin_required(user: dict = Depends(api_login_required)) -> dict:
    if user.get("permissions") != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have the required permissions to access this module.",
        )
    return user