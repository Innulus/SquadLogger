import logging
import sqlite3
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status

from services.security import verify_api_code_and_log
from database.db_logs import (
    create_main_log,
    delete_main_log,
    get_paginated_main_logs,
    update_main_log,
)
from services.db_connection import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["Logs"])


# --- Schemas ---

class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginatedLogsResponse(BaseModel):
    items: List[Dict[str, Any]]
    pagination: PaginationMeta


class LogCreateUpdate(BaseModel):
    steam_id: str
    username: str
    punishment_duration: int
    server_name: str
    reason_given: Optional[str] = None


class ReviewRequest(BaseModel):
    reviewer: str


# --- Endpoints ---

@router.get("/heartbeat")
async def get_heartbeat():
    logger.debug("Heartbeat check requested.")
    return {"status": "ok"}


@router.get("/", response_model=PaginatedLogsResponse)
async def read_logs_endpoint(
    page: int = Query(1, ge=1, description="Page number to fetch"),
    db: sqlite3.Connection = Depends(get_db)
):
    logger.info("Fetching paginated logs: page=%d", page)
    result = get_paginated_main_logs(conn=db, page=page)
    logger.debug(
        "Retrieved %d logs on page %d (total: %d)",
        len(result.get("items", [])),
        page,
        result.get("pagination", {}).get("total_count", 0)
    )
    return result


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_log_endpoint(
    payload: LogCreateUpdate,
    db: sqlite3.Connection = Depends(get_db),
    authorized_client: str = Depends(verify_api_code_and_log)
):
    logger.info(
        "Client '%s' creating log for username='%s' (SteamID=%s)",
        authorized_client,
        payload.username,
        payload.steam_id
    )
    
    new_log = create_main_log(
        conn=db, 
        steam_id=payload.steam_id, 
        username=payload.username, 
        punishment_duration=payload.punishment_duration, 
        server_name=payload.server_name,
        reason_given=payload.reason_given
    )
    
    log_id = new_log.get("id") if isinstance(new_log, dict) else "unknown"
    logger.info("Successfully created log ID %s by client '%s'", log_id, authorized_client)
    return new_log


@router.delete("/{log_id}")
async def delete_log_endpoint(
    log_id: int, 
    db: sqlite3.Connection = Depends(get_db), 
    authorized_client: str = Depends(verify_api_code_and_log)
):
    logger.info("Client '%s' attempting to delete log ID %d", authorized_client, log_id)
    success = delete_main_log(db, log_id)
    
    if not success:
        logger.warning("Failed to delete log ID %d: Not found", log_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")
        
    logger.info("Successfully deleted log ID %d by client '%s'", log_id, authorized_client)
    return {"success": True, "deleted_id": log_id}


@router.put("/{log_id}")
async def update_log_endpoint(
    log_id: int,
    payload: LogCreateUpdate,
    db: sqlite3.Connection = Depends(get_db),
    authorized_client: str = Depends(verify_api_code_and_log)
):
    logger.info("Client '%s' attempting to update log ID %d", authorized_client, log_id)
    
    updated_log = update_main_log(
        conn=db, 
        log_id=log_id,
        steam_id=payload.steam_id, 
        username=payload.username, 
        punishment_duration=payload.punishment_duration, 
        server_name=payload.server_name,
        reason_given=payload.reason_given
    )

    if not updated_log:
        logger.warning("Failed to update log ID %d: Not found", log_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")

    logger.info("Successfully updated log ID %d by client '%s'", log_id, authorized_client)
    return updated_log
