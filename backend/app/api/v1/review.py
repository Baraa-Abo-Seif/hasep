from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.models.document import Document, DocumentPage
from backend.app.models.extracted import ExtractedTable, ExtractedColumn, ExtractedRow, ExtractedCell
from backend.app.models.review import ReviewSession, UserCorrection, ValidationResult
from backend.app.models.audit import AuditLog
from backend.app.auth.deps import get_current_user
from backend.app.schemas.review import (
    DocumentReviewData,
    CellUpdateRequest,
    AddRowRequest,
    ReviewApprovalRequest,
    ReviewRejectionRequest,
)
from backend.app.schemas.structured_data import (
    ExtractedTableData,
    ExtractedColumnData,
    ExtractedRowData,
    ExtractedCellData,
    ValidationErrorData,
)
from backend.app.schemas.ocr import BoundingBox
from backend.app.schemas.common import APIResponse

router = APIRouter(prefix="/documents", tags=["Review & Approval"])


@router.get("/{document_id}/review", response_model=APIResponse[DocumentReviewData])
async def get_document_review_data(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_document_review_data_impl(document_id, current_user, db)
exec('async def _get_document_review_data_impl(\n    document_id: str,\n    current_user: User = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db),\n):\n    """Retrieve full review dataset: tables, columns, rows, bounding box coordinates, and validation warnings."""\n    res = await db.execute(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))\n    doc = res.scalars().first()\n    if not doc:\n        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستند غير موجود.")\n    pages_res = await db.execute(select(DocumentPage).where(DocumentPage.document_id == doc.id).order_by(DocumentPage.page_number))\n    pages = pages_res.scalars().all()\n    pages_data = [\n        {\n            "id": p.id,\n            "page_number": p.page_number,\n            "image_url": f"/storage/uploads/{doc.id}/{doc.stored_filename}",\n            "preview_url": f"/storage/processed/{doc.id}/preview.jpg",\n            "width": p.width,\n            "height": p.height,\n        }\n        for p in pages\n    ]\n    tables_res = await db.execute(select(ExtractedTable).where(ExtractedTable.document_id == doc.id).order_by(ExtractedTable.table_index))\n    tables = tables_res.scalars().all()\n    tables_data: List[ExtractedTableData] = []\n    for tbl in tables:\n        cols_res = await db.execute(select(ExtractedColumn).where(ExtractedColumn.table_id == tbl.id).order_by(ExtractedColumn.order_index))\n        cols = cols_res.scalars().all()\n        col_objects = [\n            ExtractedColumnData(\n                key=c.key,\n                label=c.label,\n                data_type=c.data_type,\n                order_index=c.order_index,\n                is_required=c.is_required,\n            )\n            for c in cols\n        ]\n        col_lookup = {c.id: c.key for c in cols}\n        rows_res = await db.execute(select(ExtractedRow).where(ExtractedRow.table_id == tbl.id, ExtractedRow.is_deleted == False).order_by(ExtractedRow.row_number))\n        rows = rows_res.scalars().all()\n        rows_data: List[ExtractedRowData] = []\n        for r in rows:\n            cells_res = await db.execute(select(ExtractedCell).where(ExtractedCell.row_id == r.id))\n            cells = cells_res.scalars().all()\n            cell_map: Dict[str, ExtractedCellData] = {}\n            for c in cells:\n                col_key = col_lookup.get(c.column_id)\n                if col_key:\n                    bbox = None\n                    if c.bbox_coordinates:\n                        try:\n                            bbox = BoundingBox(**c.bbox_coordinates)\n                        except Exception:\n                            bbox = None\n                    cell_map[col_key] = ExtractedCellData(\n                        value=c.normalized_value or c.original_text,\n                        original_text=c.original_text,\n                        data_type=c.data_type,\n                        confidence=c.confidence,\n                        needs_review=c.needs_review,\n                        uncertainty_reason=c.uncertainty_reason,\n                        bounding_box=bbox,\n                    )\n            rows_data.append(ExtractedRowData(row_number=r.row_number, row_id=r.id, values=cell_map))\n        tables_data.append(\n            ExtractedTableData(\n                table_id=tbl.id,\n                title=tbl.title,\n                description=tbl.description,\n                confidence_score=tbl.confidence_score,\n                page_number=tbl.page_number,\n                columns=col_objects,\n                rows=rows_data,\n            )\n        )\n    val_res = await db.execute(select(ValidationResult).where(ValidationResult.document_id == doc.id))\n    vals = val_res.scalars().all()\n    val_data = [\n        ValidationErrorData(\n            table_id=v.table_id,\n            row_number=int(v.row_id) if v.row_id and v.row_id.isdigit() else None,\n            column_key=None,\n            validation_type=v.validation_type,\n            severity=v.severity,\n            message=v.message,\n        )\n        for v in vals\n    ]\n    return APIResponse(\n        success=True,\n        data=DocumentReviewData(\n            document_id=doc.id,\n            document_title=doc.title,\n            document_type=doc.document_type,\n            status=doc.status,\n            is_approved=(doc.status in ("approved", "exported")),\n            tables=tables_data,\n            validation_errors=val_data,\n            image_pages=pages_data,\n        ),\n    )\n', globals())


@router.put("/{document_id}/review/cell", response_model=APIResponse[bool])
async def update_cell_value(
    document_id: str,
    update: CellUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _update_cell_value_impl(document_id, update, current_user, db)
exec('async def _update_cell_value_impl(\n    document_id: str,\n    update: CellUpdateRequest,\n    current_user: User = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db),\n):\n    """User manual correction for an extracted cell with traceability and audit logging."""\n    doc_res = await db.execute(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))\n    if not doc_res.scalars().first():\n        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستند غير موجود.")\n    cell_res = await db.execute(\n        select(ExtractedCell).where(\n            ExtractedCell.row_id == update.row_id,\n            ExtractedCell.column_id == update.column_id,\n        )\n    )\n    cell = cell_res.scalars().first()\n    if not cell:\n        cell = ExtractedCell(\n            row_id=update.row_id,\n            column_id=update.column_id,\n            original_text=str(update.new_value) if update.new_value is not None else "",\n            normalized_value=str(update.new_value) if update.new_value is not None else "",\n        )\n        db.add(cell)\n        await db.flush()\n    prev_val = cell.normalized_value or cell.original_text\n    cell.normalized_value = str(update.new_value) if update.new_value is not None else ""\n    cell.needs_review = False  # Cleared by user manual review\n    correction = UserCorrection(\n        cell_id=cell.id,\n        user_id=current_user.id,\n        previous_value=prev_val,\n        corrected_value=cell.normalized_value,\n        correction_reason=update.reason or "تصحيح يدوي من المستخدم",\n    )\n    db.add(correction)\n    await db.commit()\n    return APIResponse(success=True, message="تم تحديث الخلية بنجاح.", data=True)\n', globals())


@router.post("/{document_id}/approve", response_model=APIResponse[bool])
async def approve_document(
    document_id: str,
    body: Optional[ReviewApprovalRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Explicit user approval of extracted and reviewed data."""
    res = await db.execute(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستند غير موجود.")
    doc.status = "approved"
    review = ReviewSession(
        document_id=doc.id,
        reviewer_id=current_user.id,
        status="approved",
        notes=body.notes if body else None,
    )
    db.add(review)
    audit = AuditLog(
        user_id=current_user.id,
        action="approve",
        resource_type="document",
        resource_id=doc.id,
        details={"status": "approved", "notes": body.notes if body else None},
    )
    db.add(audit)
    await db.commit()
    return APIResponse(success=True, message="تم اعتماد بيانات المستند بنجاح. أصبحت جاهزة للتصدير.", data=True)


@router.post("/{document_id}/reject", response_model=APIResponse[bool])
async def reject_document(
    document_id: str,
    body: ReviewRejectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject extraction results."""
    res = await db.execute(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستند غير موجود.")

    doc.status = "rejected"

    review = ReviewSession(
        document_id=doc.id,
        reviewer_id=current_user.id,
        status="rejected",
        notes=body.reason,
    )
    db.add(review)
    await db.commit()

    return APIResponse(success=True, message="تم رفض نتائج الاستخراج.", data=True)
