from fastapi.responses import RedirectResponse, HTMLResponse, Response
from fastapi import APIRouter, Request, Form, HTTPException, status, Depends
import logging
from pathlib import Path
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from database.db_authentication import add_password_user, fetch_user_by_username, create_password_session, create_oauth_session, revoke_user_session, count_total_users
from services.config import settings, BASE_DIR
from services.security import verify_password, get_password_hash, web_login_required, get_current_user_session, get_session_token_from_request
from services.db_connection import get_db, get_db_context
import sqlite3 

logger = logging.getLogger("logs")
logging.basicConfig(level=logging.INFO)

router = APIRouter()
templates = Jinja2Templates(directory=BASE_DIR / "api" / "templates")

@router.get("/initial-setup")
async def get_initial_setup(request: Request, db: sqlite3.Connection = Depends(get_db)):
    # Check your global memory flag
    if count_total_users(db) > 0:
        # Option A: Act like the page doesn't exist anymore
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Not Found"
        )
        
        # Option B: Safely push them away to the dashboard
        # return RedirectResponse("/dashboard", status_code=303)

    context={}  

    return templates.TemplateResponse(
        request=request,
        name="initial_setup.html",
        context=context
    )

@router.post("/initial-setup", response_class=HTMLResponse)
async def post_initial_setup(
    request: Request, 
    master_app_key: str = Form(...), 
    username: str = Form(...), 
    email: str = Form(...), 
    password: str = Form(...),
    db: sqlite3.Connection = Depends(get_db)
):
    if count_total_users(db) > 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Not Found"
        )
    
    if master_app_key != settings.SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Master Application Key"
        )

    hashed_password = get_password_hash(password)
    admin_permissions = "Admin"
    add_password_user(db, email, username, hashed_password, admin_permissions)
    request.app.state.needs_setup = False

    response = Response(content="Initialization complete. Routing...")
    response.headers["HX-Redirect"] = "/login"
    return response



    

@router.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request, db: sqlite3.Connection = Depends(get_db)):

    if count_total_users(db) == 0:
        return RedirectResponse("/initial-setup", status_code=303)

    session_data = get_current_user_session(request)

    if session_data:
        valid_session_exists = await web_login_required(request)
        if valid_session_exists == True:
            logging.info(f"Session already exists! Logging in user with session token starting with: {session_data['session_token'][:6]}************")
            return RedirectResponse("/?error=already_logged_in", status_code=status.HTTP_303_SEE_OTHER)
        
        # Handles the case where a session token is in the browser but not in the database
        logging.warning("Invalid/Expired cookie detected. Clearing and reset.")
        response = templates.TemplateResponse(request=request, name="login.html")
        response.delete_cookie("session_token")
        return response
    
    context={"google_login": settings.GOOGLE_LOGIN, "discord_login": settings.DISCORD_LOGIN} 

    return templates.TemplateResponse(
    request=request, 
    name="login.html",
    context=context
)


@router.post("/login")
async def post_login_request(request: Request, username: str = Form(...), password: str = Form(...), db: sqlite3.Connection = Depends(get_db)):
    
    # NOTE: Currently this logic redirects to home even if the post request contains invalid credentials  
    if get_current_user_session(request) is True:
        logging.info(f"Redundant login attempt for active session: {username}")
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    
    username = username.strip()
    user = fetch_user_by_username(db, username)
    
    if not user or not verify_password(password, user["hashed_password"]):
        logging.info(f"Login failed for user:'{username}', invalid username or password")
        logging.info(user)
        
        if request.headers.get("HX-Request"):
            return HTMLResponse(
                content='''
                <div class="bg-red-50 border border-red-200 text-red-600 px-4 py-2 rounded-lg text-sm font-medium">
                    Invalid username or password
                </div>
                ''',
                status_code=200 # HTMX swaps content on 200 by default
            )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent")
    session_token = create_password_session(db, user["id"], user["email"], user["username"], user["permissions"], ip_address, user_agent)
    logging.info(f"Successfully created session for user: {username}")
    
    if request.headers.get("HX-Request"):
        response = Response(headers={"HX-Redirect": "/dashboard"})
    else:
        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    response.set_cookie(key="session_token", value=session_token, httponly=True, path="/")
    return response

@router.get("/register", response_class=HTMLResponse)
async def get_registration_page(request: Request):

    return templates.TemplateResponse(request, "register.html")

@router.get("/logout")
async def logout(request: Request, 
                 current_user: dict = Depends(get_current_user_session),
                 db: sqlite3.Connection = Depends(get_db)
                 ):
    
    if current_user:
        revoke_user_session(db, current_user["session_token"])

    response = RedirectResponse(
        url="/login?info=logged_out", 
        status_code=status.HTTP_302_FOUND
    )
    response.delete_cookie(key="session_token", path="/")
    logging.info(f"Logged out session {current_user['session_token']}")
    if request.headers.get("HX-Request"):
        return Response(
            headers={
                "HX-Redirect": "/login?info=logged_out",
                "Set-Cookie": response.headers.get("Set-Cookie")
            }
        )

    return response
    