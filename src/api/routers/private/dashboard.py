from fastapi.responses import RedirectResponse, HTMLResponse, Response
from fastapi.exceptions import HTTPException
from fastapi import APIRouter, Request, Depends, Form
import logging
from pathlib import Path
from fastapi.templating import Jinja2Templates
from database.db_authentication import fetch_user_session, fetch_all_active_sessions, fetch_user_session_by_id, revoke_user_session, fetch_user_permissions_by_id
from services.security import admin_required
from services.config import BASE_DIR, settings
from services.security import get_password_hash, get_current_user_session
from database.db_authentication import add_password_user, fetch_all_users
from services.db_connection import get_db, get_db_context
from database.db_system import delete_user_by_user_id, fetch_user_by_user_id, update_user_by_user_id, update_all_active_session_permissions_by_user_id
import sqlite3

logger = logging.getLogger("logs")
logging.basicConfig(level=logging.INFO)

router = APIRouter()
templates = Jinja2Templates(directory=BASE_DIR / "api" / "templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request, session_data: dict = Depends(get_current_user_session)):

    # Create context for full page refreshes
    # NOTE: Fix later, this should not be called multiple times in multiple routes. Permissions should be passed in a more global way. 
    
    user_id = session_data["user_id"]
    permissions = session_data["permissions"]
    context = {"active_fragment": "partials/dashboard_content.html", "permissions": permissions}
    
    # Path splitting: if the request comes from HTMX only a partial is returned, 
    # otherwise it returns the full page with an active_fragment variable to tell the template what to load.
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse( 
            name="partials/dashboard_content.html", 
            request=request,
            context={"permissions": permissions}
        )
    
    return templates.TemplateResponse(
        name="dashboard.html",
        request=request,
        context=context
    )



@router.get("/dashboard/users", response_class=HTMLResponse)
async def get_users(request: Request, user = Depends(admin_required), session_data: dict = Depends(get_current_user_session), db: sqlite3.Connection = Depends(get_db)):

    user_id = session_data["user_id"]
    permissions = session_data["permissions"]
    all_users = fetch_all_users(db)

    context = {"active_fragment": "partials/users_list.html", 
               "users": all_users, 
               "permissions": permissions, 
               "user_can_delete_self": settings.USER_CAN_DELETE_SELF, 
               "current_user": user_id
    }
    
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            name="partials/users_list.html", 
            request=request,
            context=context
            )
    
    return templates.TemplateResponse(
        name = "dashboard.html",
        request=request,
        context=context  
    )

@router.get("/dashboard/users/create", response_class=HTMLResponse)
async def get_create_user_form(request: Request, user = Depends(admin_required), session_data: dict = Depends(get_current_user_session)):
    permissions = session_data["permissions"]
    context = {"active_fragment": "partials/users_creation_form.html", "permissions": permissions}
    
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            name="partials/user_creation_form.html", 
            request=request,
            context=context
            )
    
    return templates.TemplateResponse(
        name = "dashboard.html",
        request=request,
        context=context  
    )

@router.post("/dashboard/users/create", response_class=HTMLResponse)
async def post_create_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    permission: str = Form(...),
    password: str = Form(...),
    user = Depends(admin_required),
    db: sqlite3.Connection = Depends(get_db)
):
    hashed_password = get_password_hash(password)
    add_password_user(db, email, username, hashed_password, permission)

    users = fetch_all_users(db) 
    context={"users": users}

    # 3. Return the full users partial to update the main-content
    return templates.TemplateResponse(
        name="partials/users_list.html", 
        request=request, 
        context=context
    )

@router.get("/dashboard/users/edit/{user_id}", response_class=HTMLResponse)
async def get_edit_user(
    request: Request,
    user_id: str,
    user = Depends(admin_required),
    db: sqlite3.Connection = Depends(get_db)
):
    user = fetch_user_by_user_id(db, user_id)

    context={"user": user}
    return templates.TemplateResponse(
        name="partials/user_edit_form.html",
        request=request,
        context=context
    )

@router.put("/dashboard/users/update/{user_id}", response_class=HTMLResponse)
async def put_edit_user(
    request: Request,
    user_id: str,
    username: str = Form(...),
    email: str = Form(...),
    permissions: str = Form(...),
    user = Depends(admin_required),
    session_data: dict = Depends(get_current_user_session),
    db: sqlite3.Connection = Depends(get_db)
):
    update_user_by_user_id(db, user_id, username, email, permissions)
    updated_user = fetch_user_by_user_id(db, user_id)
    updated_count = update_all_active_session_permissions_by_user_id(db, user_id, permissions)
    if updated_count > 0:
        logging.info(f"Updated permissions for {updated_count} active sessions belonging to User {user_id}")

    context={"user": updated_user, 
             "user_can_delete_self": settings.USER_CAN_DELETE_SELF,
             "current_user": session_data["user_id"]}
    
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            name="partials/user_row.html", 
            request=request,
            context=context
            )
    
    return templates.TemplateResponse(
        name = "dashboard.html",
        request=request,
        context=context 
    )

@router.get("/dashboard/users/row/{user_id}", response_class=HTMLResponse)
async def get_user_row(
    request: Request,
    user_id: str,
    user = Depends(admin_required), 
    session_data: dict = Depends(get_current_user_session),
    db: sqlite3.Connection = Depends(get_db)
):
    user = fetch_user_by_user_id(db, user_id)
    context= {"user": user, 
             "user_can_delete_self": settings.USER_CAN_DELETE_SELF,
             "current_user": session_data["user_id"]
    }

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            name="partials/user_row.html", 
            request=request,
            context=context
    )
    return templates.TemplateResponse(
        name = "dashboard.html",
        request=request,
        context=context
    )


@router.delete("/dashboard/users/delete/{user_id_to_delete}")
async def post_delete_user(
    request: Request,
    user_id_to_delete: str,
    user = Depends(admin_required), 
    session_data: dict = Depends(get_current_user_session),
    db: sqlite3.Connection = Depends(get_db)
):
    user_id = session_data["user_id"]

    if settings.USER_CAN_DELETE_SELF == False:
        if user_id == user_id_to_delete:
            return templates.TemplateResponse(
                name="partials/users_list.html", 
                request=request, 
                context={
                    "users": fetch_all_users(db),
                    "error": "You are not allowed to delete your own account."
                },
                status_code=400
            )

    delete_user_by_user_id(db, user_id_to_delete)
    users = fetch_all_users(db) 
    context = {"users:": users}

    # 3. Return the full users partial to update the main-content
    return templates.TemplateResponse(
        name="partials/users_list.html", 
        request=request, 
        context=context
    )

@router.get("/dashboard/session-management", response_class=HTMLResponse)
async def get_session_management(request: Request, user = Depends(admin_required), session_data: dict = Depends(get_current_user_session), db: sqlite3.Connection = Depends(get_db)):

    # Create context for full page refreshes
    user_id = session_data["user_id"]
    permissions = session_data["permissions"]
    active_sessions = fetch_all_active_sessions(db)

    # Create context for full page refreshes
    context = {"active_fragment": "partials/sessions_list.html", "active_sessions": active_sessions, "permissions": permissions}

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            name="partials/sessions_list.html", 
            request=request,
            context=context
            )
    
    return templates.TemplateResponse(
        name = "dashboard.html",
        request=request,
        context=context  
    )


@router.post("/dashboard/revoke-session/{session_id}")
async def post_revoke_session(request: Request, session_id:int, user = Depends(admin_required), db: sqlite3.Connection = Depends(get_db)):
    target_session = fetch_user_session_by_id(db, session_id)
    print(target_session)
    
    if not target_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    revoke_user_session(db, target_session["session_token"])
    is_current_session = target_session["session_token"] == request.cookies.get("session_token")

    if is_current_session:
        response = Response(status_code=200, headers={"HX-Redirect": "/login?error=session_terminated"})
        response.delete_cookie("session_token")
        return response
    
    return Response(status_code=200)

