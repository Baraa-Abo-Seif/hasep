import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.models.document import Document, DocumentPage
from backend.app.auth.deps import get_current_user
from backend.app.services.document_service import DocumentService
from backend.app.workers.pipeline import run_document_processing_pipeline
from backend.app.schemas.document import DocumentResponse, DocumentPageInfo, DocumentUpdatePayload
from backend.app.schemas.common import APIResponse, PaginatedResponse
from backend.app.core.config import settings

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=APIResponse[List[DocumentResponse]])
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    auto_process: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _upload_documents_impl(background_tasks, files, auto_process, current_user, db)
exec('async def _upload_documents_impl(\n    background_tasks: BackgroundTasks,\n    files: List[UploadFile] = File(...),\n    auto_process: bool = Query(True),\n    current_user: User = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db),\n):\n    """Upload one or multiple images/documents (JPEG, PNG, WebP, PDF).\n    Automatically triggers background processing if auto_process=True.\n    """\n    if not files:\n        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided for upload.")\n    uploaded_docs: List[Document] = []\n    errors: List[str] = []\n    for f in files:\n        try:\n            doc = await DocumentService.create_document(db=db, user_id=current_user.id, upload_file=f)\n            uploaded_docs.append(doc)\n            if auto_process:\n                background_tasks.add_task(run_document_processing_pipeline, doc.id)\n        except Exception as e:\n            errors.append(f"Error processing {f.filename}: {str(e)}")\n    if not uploaded_docs and errors:\n        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(errors))\n    result_list = []\n    for d in uploaded_docs:\n        pages_res = await db.execute(select(DocumentPage).where(DocumentPage.document_id == d.id).order_by(DocumentPage.page_number))\n        pages = pages_res.scalars().all()\n        pages_info = [\n            DocumentPageInfo(\n                id=p.id,\n                page_number=p.page_number,\n                image_url=f"/storage/uploads/{d.id}/{d.stored_filename}",\n                preview_url=f"/storage/processed/{d.id}/preview.jpg",\n                width=p.width,\n                height=p.height,\n            )\n            for p in pages\n        ]\n        result_list.append(\n            DocumentResponse(\n                id=d.id,\n                title=d.title,\n                original_filename=d.original_filename,\n                file_size=d.file_size,\n                mime_type=d.mime_type,\n                document_type=d.document_type,\n                status=d.status,\n                error_message=d.error_message,\n                pages=pages_info,\n                created_at=d.created_at,\n                updated_at=d.updated_at,\n            )\n        )\n    return APIResponse(\n        success=True,\n        message=f"تم رفع {len(uploaded_docs)} مستند بنجاح.",\n        data=result_list,\n        errors=errors if errors else None,\n    )\n', globals())


@router.get("", response_model=PaginatedResponse[DocumentResponse])
async def list_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _list_documents_impl(page, limit, status_filter, current_user, db)
exec('async def _list_documents_impl(\n    page: int = Query(1, ge=1),\n    limit: int = Query(20, ge=1, le=100),\n    status_filter: Optional[str] = Query(None, alias="status"),\n    current_user: User = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db),\n):\n    """List documents belonging to authenticated user with pagination and status filter."""\n    base_query = select(Document).where(Document.user_id == current_user.id)\n    if status_filter:\n        base_query = base_query.where(Document.status == status_filter)\n    count_query = select(func.count()).select_from(base_query.subquery())\n    total_count = (await db.execute(count_query)).scalar() or 0\n    offset = (page - 1) * limit\n    paginated_query = base_query.order_by(desc(Document.created_at)).offset(offset).limit(limit)\n    res = await db.execute(paginated_query)\n    docs = res.scalars().all()\n    items = []\n    for d in docs:\n        pages_res = await db.execute(select(DocumentPage).where(DocumentPage.document_id == d.id).order_by(DocumentPage.page_number))\n        pages = pages_res.scalars().all()\n        pages_info = [\n            DocumentPageInfo(\n                id=p.id,\n                page_number=p.page_number,\n                image_url=f"/storage/uploads/{d.id}/{d.stored_filename}",\n                preview_url=f"/storage/processed/{d.id}/preview.jpg",\n                width=p.width,\n                height=p.height,\n            )\n            for p in pages\n        ]\n        items.append(\n            DocumentResponse(\n                id=d.id,\n                title=d.title,\n                original_filename=d.original_filename,\n                file_size=d.file_size,\n                mime_type=d.mime_type,\n                document_type=d.document_type,\n                status=d.status,\n                error_message=d.error_message,\n                pages=pages_info,\n                created_at=d.created_at,\n                updated_at=d.updated_at,\n            )\n        )\n    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1\n    return PaginatedResponse(\n        items=items,\n        total=total_count,\n        page=page,\n        limit=limit,\n        total_pages=total_pages,\n    )\n', globals())


@router.get("/{document_id}", response_model=APIResponse[DocumentResponse])
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_document_impl(document_id, current_user, db)
exec('async def _get_document_impl(\n    document_id: str,\n    current_user: User = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db),\n):\n    """Retrieve details of a single document."""\n    res = await db.execute(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))\n    doc = res.scalars().first()\n    if not doc:\n        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستند غير موجود.")\n    pages_res = await db.execute(select(DocumentPage).where(DocumentPage.document_id == doc.id).order_by(DocumentPage.page_number))\n    pages = pages_res.scalars().all()\n    pages_info = [\n        DocumentPageInfo(\n            id=p.id,\n            page_number=p.page_number,\n            image_url=f"/storage/uploads/{doc.id}/{doc.stored_filename}",\n            preview_url=f"/storage/processed/{doc.id}/preview.jpg",\n            width=p.width,\n            height=p.height,\n        )\n        for p in pages\n    ]\n    return APIResponse(\n        success=True,\n        data=DocumentResponse(\n            id=doc.id,\n            title=doc.title,\n            original_filename=doc.original_filename,\n            file_size=doc.file_size,\n            mime_type=doc.mime_type,\n            document_type=doc.document_type,\n            status=doc.status,\n            error_message=doc.error_message,\n            pages=pages_info,\n            created_at=doc.created_at,\n            updated_at=doc.updated_at,\n        ),\n    )\n', globals())


@router.delete("/{document_id}", response_model=APIResponse[bool])
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete document, database records, and disk files."""
    res = await db.execute(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستند غير موجود.")

    # Remove disk directories
    upload_dir = os.path.dirname(doc.file_path) if doc.file_path else None
    processed_dir = os.path.join(settings.STORAGE_DIR, "processed", doc.id)

    if upload_dir and os.path.isdir(upload_dir):
        shutil.rmtree(upload_dir, ignore_errors=True)
    if os.path.isdir(processed_dir):
        shutil.rmtree(processed_dir, ignore_errors=True)

    await db.delete(doc)
    await db.commit()

    return APIResponse(success=True, message="تم حذف المستند بنجاح.", data=True)


@router.put("/{document_id}", response_model=APIResponse[DocumentResponse])
async def update_document(
    document_id: str,
    payload: DocumentUpdatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _update_document_impl(document_id, payload, current_user, db)
exec('async def _update_document_impl(\n    document_id: str,\n    payload: DocumentUpdatePayload,\n    current_user: User = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db),\n):\n    """Update editable document metadata; date remains controlled by the system."""\n    res = await db.execute(\n        select(Document).where(Document.id == document_id, Document.user_id == current_user.id)\n    )\n    doc = res.scalars().first()\n    if not doc:\n        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستند غير موجود.")\n    if payload.title is not None:\n        title = payload.title.strip()\n        if not title:\n            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم المستند لا يمكن أن يكون فارغاً.")\n        doc.title = title[:255]\n    if payload.document_type is not None:\n        doc.document_type = payload.document_type.strip()[:50] or "other"\n    await db.commit()\n    await db.refresh(doc)\n    return APIResponse(\n        success=True,\n        message="تم تحديث بيانات المستند.",\n        data=DocumentResponse(\n            id=doc.id,\n            title=doc.title,\n            original_filename=doc.original_filename,\n            file_size=doc.file_size,\n            mime_type=doc.mime_type,\n            document_type=doc.document_type,\n            status=doc.status,\n            error_message=doc.error_message,\n            pages=[],\n            created_at=doc.created_at,\n            updated_at=doc.updated_at,\n        ),\n    )\n', globals())
