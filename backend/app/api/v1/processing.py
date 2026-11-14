from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.models.document import Document, ProcessingJob
from backend.app.auth.deps import get_current_user
from backend.app.workers.pipeline import run_document_processing_pipeline
from backend.app.schemas.document import DocumentProcessingStatus
from backend.app.schemas.common import APIResponse

router = APIRouter(prefix="/documents", tags=["Processing"])


@router.post("/{document_id}/process", response_model=APIResponse[DocumentProcessingStatus])
async def process_document_endpoint(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger background document processing pipeline."""
    res = await db.execute(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستند غير موجود.")

    background_tasks.add_task(run_document_processing_pipeline, document_id)

    return APIResponse(
        success=True,
        message="تم بدء عملية المعالجة بنجاح.",
        data=DocumentProcessingStatus(
            document_id=doc.id,
            status="queued",
            progress_percentage=5,
            stage="تم جدولة المعالجة",
        ),
    )


@router.get("/{document_id}/status", response_model=APIResponse[DocumentProcessingStatus])
async def get_processing_status(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get real-time processing status and progress for a document."""
    res = await db.execute(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستند غير موجود.")
    job_res = await db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.document_id == document_id)
        .order_by(ProcessingJob.created_at.desc())
    )
    job = job_res.scalars().first()
    progress = job.progress_percentage if job else (100 if doc.status == "ready_for_review" else 0)
    stage = job.stage_description if job else doc.status
    return APIResponse(
        success=True,
        data=DocumentProcessingStatus(
            document_id=doc.id,
            status=doc.status,
            progress_percentage=progress,
            stage=stage,
            error_message=doc.error_message,
        ),
    )


@router.post("/{document_id}/retry", response_model=APIResponse[DocumentProcessingStatus])
async def retry_processing(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retry failed processing pipeline."""
    res = await db.execute(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستند غير موجود.")

    doc.status = "queued"
    doc.error_message = None
    await db.commit()

    background_tasks.add_task(run_document_processing_pipeline, document_id)

    return APIResponse(
        success=True,
        message="تمت إعادة محاولة معالجة المستند بنجاح.",
        data=DocumentProcessingStatus(
            document_id=doc.id,
            status="queued",
            progress_percentage=0,
            stage="إعادة المعالجة قيد التنفيذ",
        ),
    )
