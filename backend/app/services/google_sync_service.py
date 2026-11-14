"""
Google Sheets Background Synchronization Service for Project # hasep.
Guarantees durable, idempotent, transaction-safe background syncing of approved financial records.
Enforces:
1. Sync ONLY after Final Approval.
2. Safe SQLite/Postgres atomic queue management.
3. Exponential backoff retry logic.
4. Automatic spreadsheet creation or selection.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from backend.app.core.config import settings
from backend.app.models.financial_record import FinancialRecord
from backend.app.models.google_sync import GoogleSheetsSyncJob
from backend.app.models.google_connection import GoogleConnection
from backend.app.schemas.financial_form import FinancialFormData
from backend.app.integrations.google.auth import GoogleAuthService
from backend.app.integrations.google.sheets import GoogleSheetsService

logger = logging.getLogger("arabic_excel_platform.google_sync_service")


class GoogleSyncManager:
    @staticmethod
    async def create_or_get_sync_job(
        db: AsyncSession,
        record: FinancialRecord,
    ) -> GoogleSheetsSyncJob:
        return await _GoogleSyncManager_create_or_get_sync_job_impl(db, record)

    @staticmethod
    async def execute_sync_job(
        db: AsyncSession,
        job_id: str,
    ) -> Dict[str, Any]:
        return await _GoogleSyncManager_execute_sync_job_impl(db, job_id)

    @staticmethod
    async def _count_jobs(db: AsyncSession, statuses) -> int:
        query = select(func.count(GoogleSheetsSyncJob.id))
        if statuses:
            condition = (
                GoogleSheetsSyncJob.status.in_(statuses)
                if isinstance(statuses, list)
                else GoogleSheetsSyncJob.status == statuses
            )
            query = query.where(condition)
        result = await db.execute(query)
        return result.scalar() or 0

    @staticmethod
    async def get_sync_stats(db: AsyncSession) -> Dict[str, Any]:
        """Returns statistics for Google Sheets sync queue."""
        total = await GoogleSyncManager._count_jobs(db, None)
        pending = await GoogleSyncManager._count_jobs(db, ["PENDING", "RETRY"])
        success = await GoogleSyncManager._count_jobs(db, "SUCCESS")
        failed = await GoogleSyncManager._count_jobs(db, "FAILED")
        last_sync_q = await db.execute(
            select(GoogleSheetsSyncJob.synced_at)
            .where(GoogleSheetsSyncJob.status == "SUCCESS")
            .order_by(GoogleSheetsSyncJob.synced_at.desc())
            .limit(1)
        )
        last_sync = last_sync_q.scalar()
        return {
            "total_jobs": total,
            "pending_count": pending,
            "success_count": success,
            "failed_count": failed,
            "last_synced_at": last_sync.isoformat() if last_sync else None,
        }

exec('async def _GoogleSyncManager_execute_sync_job_impl(\n    db: AsyncSession,\n    job_id: str,\n) -> Dict[str, Any]:\n    """\n    Executes a single Google Sheets sync job.\n    Handles token verification, spreadsheet determination, native formula insertion,\n    error tracking, and backoff scheduling.\n    """\n    res = await db.execute(\n        select(GoogleSheetsSyncJob).where(GoogleSheetsSyncJob.id == job_id)\n    )\n    job = res.scalars().first()\n    if not job:\n        return {"success": False, "error": f"Job {job_id} not found."}\n    rec_res = await db.execute(\n        select(FinancialRecord).where(FinancialRecord.id == job.approved_record_id)\n    )\n    record = rec_res.scalars().first()\n    if not record:\n        job.status = "FAILED"\n        job.last_error = "Associated FinancialRecord not found."\n        await db.commit()\n        return {"success": False, "error": job.last_error}\n    if not record.is_approved:\n        job.status = "FAILED"\n        job.last_error = "CRITICAL: Attempted to sync unapproved financial record to Google Sheets."\n        logger.error(job.last_error)\n        await db.commit()\n        return {"success": False, "error": job.last_error}\n    job.status = "PROCESSING"\n    job.updated_at = datetime.now(timezone.utc)\n    await db.commit()\n    auth_service = GoogleAuthService()\n    if not auth_service.is_configured():\n        job.status = "PENDING"\n        job.last_error = "Google OAuth credentials are not configured in system settings."\n        record.google_sync_status = "unconfigured"\n        await db.commit()\n        return {"success": False, "error": job.last_error}\n    creds = await auth_service.get_valid_credentials(db, record.user_id)\n    if not creds:\n        job.status = "PENDING"\n        job.last_error = "حساب Google غير متصل أو منتهي الصلاحية. يرجى إعادة الاتصال من صفحة الإعدادات."\n        record.google_sync_status = "unconfigured"\n        await db.commit()\n        return {"success": False, "error": job.last_error}\n    try:\n        sheets_service = GoogleSheetsService(creds)\n        spreadsheet_id = job.spreadsheet_id or settings.GOOGLE_SPREADSHEET_ID\n        if not spreadsheet_id:\n            spreadsheet_id = sheets_service.get_or_create_spreadsheet("# hasep Financial Records")\n            job.spreadsheet_id = spreadsheet_id\n        form = FinancialFormData.model_validate(record.form_data)\n        sync_result = sheets_service.append_daily_block(\n            spreadsheet_id=spreadsheet_id,\n            form=form,\n            record_id=record.id,\n        )\n        job.status = "SUCCESS"\n        job.synced_at = datetime.now(timezone.utc)\n        job.target_sheet_name = sync_result.get("sheet_name")\n        job.last_error = None\n        record.google_sync_status = "synced"\n        record.google_synced_at = datetime.now(timezone.utc)\n        await db.commit()\n        logger.info(f"Google sync job {job_id} succeeded for record {record.id}.")\n        return {"success": True, "details": sync_result}\n    except Exception as e:\n        logger.error(f"Error syncing record {record.id} to Google Sheets: {e}", exc_info=True)\n        job.retry_count += 1\n        job.last_error = str(e)\n        if job.retry_count >= job.max_retries:\n            job.status = "FAILED"\n            record.google_sync_status = "failed"\n        else:\n            job.status = "RETRY"\n            backoff_seconds = min(3600, (2 ** job.retry_count) * 15)\n            job.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)\n            record.google_sync_status = "pending"\n        await db.commit()\n        return {"success": False, "error": str(e), "retry_count": job.retry_count}\n', globals())
exec('async def _GoogleSyncManager_create_or_get_sync_job_impl(\n    db: AsyncSession,\n    record: FinancialRecord,\n) -> GoogleSheetsSyncJob:\n    """\n    Creates or retrieves an idempotent GoogleSheetsSyncJob for the approved record.\n    MUST ONLY be called within the same database transaction as final approval.\n    """\n    if not record.is_approved:\n        raise ValueError(f"Cannot queue Google Sheets sync for unapproved record {record.id}")\n    idempotency_key = f"aya_gsheet_{record.id}"\n    res = await db.execute(\n        select(GoogleSheetsSyncJob).where(\n            or_(\n                GoogleSheetsSyncJob.approved_record_id == record.id,\n                GoogleSheetsSyncJob.idempotency_key == idempotency_key,\n            )\n        )\n    )\n    existing_job = res.scalars().first()\n    if existing_job:\n        return existing_job\n    conn_res = await db.execute(\n        select(GoogleConnection).where(\n            GoogleConnection.user_id == record.user_id,\n            GoogleConnection.is_active == True,\n        )\n    )\n    has_active_conn = conn_res.scalars().first() is not None\n    new_job = GoogleSheetsSyncJob(\n        approved_record_id=record.id,\n        spreadsheet_id=settings.GOOGLE_SPREADSHEET_ID,\n        target_sheet_name=record.form_date,\n        idempotency_key=idempotency_key,\n        status="PENDING",\n        retry_count=0,\n        max_retries=5,\n        last_error=None if has_active_conn else "حساب Google غير متصل حالياً. بانتظار ربط الحساب من الإعدادات.",\n        next_retry_at=datetime.now(timezone.utc),\n    )\n    db.add(new_job)\n    record.google_sync_status = "pending"\n    return new_job\n', globals())
