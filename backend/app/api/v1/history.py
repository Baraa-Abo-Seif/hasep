from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.google_sync import GoogleSheetsSyncJob
from backend.app.models.audit import AuditLog
from backend.app.auth.deps import get_current_user
from backend.app.schemas.common import APIResponse

router = APIRouter(prefix="/history", tags=["History & Audit"])


@router.get("/stats", response_model=APIResponse[dict])
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_dashboard_stats_impl(current_user, db)
exec('async def _get_dashboard_stats_impl(\n    current_user: User = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db),\n):\n    """Retrieve summarized statistics for dashboard KPI cards."""\n    doc_count_res = await db.execute(\n        select(func.count()).select_from(Document).where(Document.user_id == current_user.id)\n    )\n    total_docs = doc_count_res.scalar() or 0\n    pending_res = await db.execute(\n        select(func.count())\n        .select_from(Document)\n        .where(Document.user_id == current_user.id, Document.status.in_(["ready_for_review", "ocr_completed"]))\n    )\n    pending_reviews = pending_res.scalar() or 0\n    exports_res = await db.execute(\n        select(func.count())\n        .select_from(GoogleSheetsSyncJob)\n        .where(GoogleSheetsSyncJob.status == "SUCCESS")\n    )\n    successful_exports = exports_res.scalar() or 0\n    failed_res = await db.execute(\n        select(func.count())\n        .select_from(Document)\n        .where(Document.user_id == current_user.id, Document.status == "failed")\n    )\n    failed_ops = failed_res.scalar() or 0\n    return APIResponse(\n        success=True,\n        data={\n            "total_documents": total_docs,\n            "pending_reviews": pending_reviews,\n            "successful_exports": successful_exports,\n            "failed_operations": failed_ops,\n        },\n    )\n', globals())


@router.get("", response_model=APIResponse[List[dict]])
async def list_audit_history(
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List activity and audit logs for current user."""
    res = await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == current_user.id)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )
    logs = res.scalars().all()
    data = [
        {
            "id": log.id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
    return APIResponse(success=True, data=data)
