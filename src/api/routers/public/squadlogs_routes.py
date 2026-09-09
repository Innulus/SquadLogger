import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from services.config import BASE_DIR
from services.security import verify_api_code_and_log

# Assuming you have your DB dependency in a file called db_connection.py
from database.db_logs import (
    create_main_log,
    delete_main_log,
    get_all_main_logs,
    update_main_log,
    review_main_log
)
from services.db_connection import get_db, get_db_context

router = APIRouter(prefix="/logs", tags=["Logs"])
templates = Jinja2Templates(directory=BASE_DIR / "api" / "templates")


@router.get("/", response_class=HTMLResponse)
async def read_logs_page(request: Request, db: sqlite3.Connection = Depends(get_db)):
    logs = get_all_main_logs(db)
    return templates.TemplateResponse(
        request=request,
        name="logs.html",
        context={"logs": logs},
    )


@router.post("/", response_class=HTMLResponse)
async def create_log_endpoint(
    request: Request,
    steam_id: str = Form(...),
    username: str = Form(...),
    punishment_duration: int = Form(...),
    server_name: str = Form(...),
    reason_given: Optional[str] = Form(None),
    issued_by: Optional[str] = Form(None),
    review: Optional[str] = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    authorized_client: str = Depends(verify_api_code_and_log)
):
    new_log = create_main_log(
        conn=db, 
        steam_id=steam_id, 
        username=username, 
        punishment_duration=punishment_duration, 
        server_name=server_name,
        reason_given=reason_given,
        issued_by=issued_by,
        review=review
    )

    # Return just the HTML row snippet for HTMX to append to the table
    return templates.TemplateResponse(
        request=request,
        name="partials/log_row.html",
        context={"log": new_log},
    )


@router.delete("/{log_id}", response_class=Response)
async def delete_log_endpoint(
    log_id: int, 
    db: sqlite3.Connection = Depends(get_db), 
    authorized_client: str = Depends(verify_api_code_and_log)
):
    success = delete_main_log(db, log_id)
    if success:
        # Return an empty 200 OK response.
        # HTMX will swap the target row with this empty response (deleting it).
        return Response(status_code=status.HTTP_200_OK)
    return Response(status_code=status.HTTP_400_BAD_REQUEST)

@router.put("/{log_id}", response_class=HTMLResponse)
async def update_log_endpoint(
    request: Request,
    log_id: int,
    steam_id: str = Form(...),
    username: str = Form(...),
    punishment_duration: int = Form(...),
    server_name: str = Form(...),
    reason_given: Optional[str] = Form(None),
    issued_by: Optional[str] = Form(None),
    review: Optional[str] = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    authorized_client: str = Depends(verify_api_code_and_log)
):
    updated_log = update_main_log(
        conn=db, 
        log_id=log_id,
        steam_id=steam_id, 
        username=username, 
        punishment_duration=punishment_duration, 
        server_name=server_name,
        reason_given=reason_given,
        issued_by=issued_by,
        review=review
    )

    if not updated_log:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    # Return the updated HTML row snippet for HTMX to swap into the table
    return templates.TemplateResponse(
        request=request,
        name="partials/log_row.html",
        context={"log": updated_log},
    )

@router.patch("/{log_id}/review", response_class=Response)
async def apply_review_endpoint(
    log_id: int,
    reviewer: str = Form(...),
    db: sqlite3.Connection = Depends(get_db),
    authorized_client: str = Depends(verify_api_code_and_log)
):
    updated_log = review_main_log(db, log_id, reviewer)
    
    if not updated_log:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
        
    return Response(status_code=status.HTTP_200_OK)