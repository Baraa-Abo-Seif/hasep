"""
Google Sheets Management and Synchronization API Endpoints for Project # hasep.
Enables monitoring sync queues, triggering retries, and configuring target spreadsheets.
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.models.google_connection import GoogleConnection
from backend.app.models.google_sync import GoogleSheetsSyncJob
from backend.app.models.financial_record import FinancialRecord
from backend.app.auth.deps import get_current_user
from backend.app.core.config import settings
from backend.app.schemas.common import APIResponse
from backend.app.services.google_sync_service import GoogleSyncManager
from backend.app.integrations.google.auth import GoogleAuthService
from backend.app.integrations.google.sheets import GoogleSheetsService

logger = logging.getLogger("arabic_excel_platform.google_sheets_api")

router = APIRouter(prefix="/google-sheets", tags=["Google Sheets Synchronization"])


class ConnectSpreadsheetPayload(BaseModel):
    spreadsheet_id: Optional[str] = None


@router.get("/status", response_model=APIResponse[dict])
async def get_google_sheets_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_google_sheets_status_impl(current_user, db)
exec('async def _get_google_sheets_status_impl(\n    current_user: User = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db),\n):\n    """Get complete Google Sheets status, target spreadsheet info, and sync queue stats."""\n    res = await db.execute(\n        select(GoogleConnection).where(\n            GoogleConnection.user_id == current_user.id,\n            GoogleConnection.is_active == True,\n        )\n    )\n    conn = res.scalars().first()\n    stats = await GoogleSyncManager.get_sync_stats(db)\n    spreadsheet_id = settings.GOOGLE_SPREADSHEET_ID\n    if not spreadsheet_id:\n        job_res = await db.execute(\n            select(GoogleSheetsSyncJob.spreadsheet_id)\n            .where(GoogleSheetsSyncJob.spreadsheet_id.isnot(None))\n            .order_by(GoogleSheetsSyncJob.updated_at.desc())\n            .limit(1)\n        )\n        spreadsheet_id = job_res.scalar()\n    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}" if spreadsheet_id else None\n    return APIResponse(\n        success=True,\n        data={\n            "is_connected": conn is not None,\n            "connected_email": conn.google_email if conn else None,\n            "display_name": conn.display_name if conn else None,\n            "expires_at": conn.expires_at.isoformat() if conn else None,\n            "spreadsheet_id": spreadsheet_id,\n            "spreadsheet_url": sheet_url,\n            "sync_stats": stats,\n        },\n    )\n', globals())


@router.post("/connect-spreadsheet", response_model=APIResponse[dict])
async def connect_spreadsheet(
    payload: ConnectSpreadsheetPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _connect_spreadsheet_impl(payload, current_user, db)
exec('async def _connect_spreadsheet_impl(\n    payload: ConnectSpreadsheetPayload,\n    current_user: User = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db),\n):\n    """\n    Connect or verify a target Google Spreadsheet.\n    If no spreadsheet_id is provided, automatically creates a new one titled \'# hasep Financial Records\'.\n    """\n    auth_service = GoogleAuthService()\n    creds = await auth_service.get_valid_credentials(db, current_user.id)\n    if not creds:\n        raise HTTPException(\n            status_code=status.HTTP_400_BAD_REQUEST,\n            detail="يرجى ربط حساب Google أولاً قبل إعداد ملف Google Sheets.",\n        )\n    sheets_service = GoogleSheetsService(creds)\n    target_id = payload.spreadsheet_id.strip() if payload.spreadsheet_id else None\n    if not target_id:\n        target_id = sheets_service.get_or_create_spreadsheet("# hasep Financial Records")\n    else:\n        try:\n            sheets_service.service.spreadsheets().get(spreadsheetId=target_id).execute()\n        except Exception as e:\n            raise HTTPException(\n                status_code=status.HTTP_400_BAD_REQUEST,\n                detail=f"تعذر الوصول إلى جدول البيانات المحدد ({target_id}): {str(e)}",\n            )\n    settings.GOOGLE_SPREADSHEET_ID = target_id\n    sheet_url = f"https://docs.google.com/spreadsheets/d/{target_id}"\n    return APIResponse(\n        success=True,\n        message="تم ربط ملف Google Sheets بنجاح.",\n        data={"spreadsheet_id": target_id, "spreadsheet_url": sheet_url},\n    )\n', globals())


@router.get("/sync-jobs", response_model=APIResponse[List[dict]])
async def list_sync_jobs(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List recent Google Sheets sync jobs."""
    res = await db.execute(
        select(GoogleSheetsSyncJob)
        .order_by(GoogleSheetsSyncJob.created_at.desc())
        .limit(limit)
    )
    jobs = res.scalars().all()
    items = []
    for j in jobs:
        items.append({
            "id": j.id,
            "approved_record_id": j.approved_record_id,
            "spreadsheet_id": j.spreadsheet_id,
            "target_sheet_name": j.target_sheet_name,
            "idempotency_key": j.idempotency_key,
            "status": j.status,
            "retry_count": j.retry_count,
            "max_retries": j.max_retries,
            "last_error": j.last_error,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "updated_at": j.updated_at.isoformat() if j.updated_at else None,
            "synced_at": j.synced_at.isoformat() if j.synced_at else None,
        })
    return APIResponse(success=True, data=items)


@router.delete("/sync-jobs/{job_id}", response_model=APIResponse[bool])
async def delete_sync_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an owned synchronization entry or a stale orphaned entry."""
    job_res = await db.execute(
        select(GoogleSheetsSyncJob).where(GoogleSheetsSyncJob.id == job_id)
    )
    job = job_res.scalars().first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مهمة المزامنة غير موجودة.")

    record_res = await db.execute(
        select(FinancialRecord).where(FinancialRecord.id == job.approved_record_id)
    )
    record = record_res.scalars().first()
    if record and record.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مهمة المزامنة غير موجودة.")

    if record is None:
        logger.info("Deleting stale orphaned Google sync job %s.", job_id)

    await db.delete(job)
    await db.commit()
    return APIResponse(success=True, message="تم حذف مهمة المزامنة.", data=True)


@router.post("/sync-jobs/{job_id}/retry", response_model=APIResponse[dict])
async def retry_sync_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger immediate retry of a specific sync job."""
    result = await GoogleSyncManager.execute_sync_job(db, job_id)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"فشلت المزامنة: {result.get('error')}",
        )
    return APIResponse(success=True, message="تمت المزامنة بنجاح إلى Google Sheets.", data=result)


@router.post("/sync-jobs/retry-pending", response_model=APIResponse[dict])
async def retry_all_pending(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger retry for all pending, retrying, or failed sync jobs."""
    res = await db.execute(
        select(GoogleSheetsSyncJob).where(
            GoogleSheetsSyncJob.status.in_(["PENDING", "RETRY", "FAILED"])
        )
    )
    jobs = res.scalars().all()

    success_count = 0
    fail_count = 0
    for j in jobs:
        r = await GoogleSyncManager.execute_sync_job(db, j.id)
        if r.get("success"):
            success_count += 1
        else:
            fail_count += 1

    return APIResponse(
        success=True,
        message=f"تمت إعادة محاولة {len(jobs)} مهمة: {success_count} نجحت، {fail_count} فشلت.",
        data={"total": len(jobs), "success": success_count, "failed": fail_count},
    )
