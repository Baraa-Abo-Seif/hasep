"""
Financial Form and Digital Review API endpoints for Project # hasep.
Behavior:
- Replaces any previous approved record for the same calendar date.
- Real-time deterministic recalculation on field update.
- Resolution of OCR uncertainties.
- Generation of Arabic RTL PDF report.
- Appending daily block to monthly Excel workbook.
- Automatic deletion of temporary uploaded images upon approval.
"""

import os
import shutil
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from backend.app.core.config import settings
from backend.app.database.session import get_db, AsyncSessionLocal
from backend.app.models.user import User
from backend.app.models.document import Document, DocumentPage
from backend.app.models.financial_record import FinancialRecord
from backend.app.models.audit import AuditLog
from backend.app.auth.deps import get_current_user
from backend.app.schemas.common import APIResponse
from backend.app.schemas.financial_form import (
    FinancialFormData,
    FieldUpdatePayload,
    ResolveUncertaintyPayload,
    FormApprovalPayload,
    EmployeeAttendanceItem,
    PurchaseItem,
    ExpenseItem,
    round_decimal,
)
from backend.app.services.financial_calculator import recalculate_financial_form
from backend.app.services.attendance_calculator import calculate_work_duration
from backend.app.services.pdf_generator import generate_financial_form_pdf
from backend.app.excel.monthly_sync import append_daily_block_to_workbook
from backend.app.services.google_sync_service import GoogleSyncManager


async def _run_google_sync_background(job_id: str):
    """Background runner for Google Sheets synchronization using isolated session."""
    async with AsyncSessionLocal() as session:
        try:
            await GoogleSyncManager.execute_sync_job(session, job_id)
        except Exception as e:
            logger.error(f"Error in background Google sync task: {e}")
from backend.app.utils.date_utils import parse_and_validate_form_date, get_current_amman_date

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Financial Forms & Review"])


def _apply_nested_field_update(form: FinancialFormData, field_path: str, value: Any) -> FinancialFormData:
    """Applies a field update to the Pydantic form using dot notation path."""
    parts = field_path.split(".")
    if parts[0] == "form_date":
        _update_form_date(form, value)
    elif parts[0] in ("attendance", "purchases", "expenses"):
        _update_indexed_item(form, parts, value)
    elif parts[0] == "sales":
        setattr(form.sales, parts[1], round_decimal(value))
    elif parts[0] == "summary":
        _update_summary(form, parts[1], value)
    return recalculate_financial_form(form)


def _update_form_date(form: FinancialFormData, value: Any) -> None:
    today = get_current_amman_date().strftime("%Y-%m-%d")
    if str(value) != today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"تاريخ النموذج يجب أن يكون تاريخ اليوم فقط ({today}).",
        )
    date_obj, derived_weekday = parse_and_validate_form_date(str(value))
    form.form_date = date_obj.strftime("%Y-%m-%d")
    form.day_of_week = derived_weekday


def _update_indexed_item(form: FinancialFormData, parts: List[str], value: Any) -> None:
    collection_name, index_text, subfield = parts[:3]
    collection = getattr(form, collection_name)
    idx = int(index_text)
    item_type = {"attendance": EmployeeAttendanceItem,
                 "purchases": PurchaseItem, "expenses": ExpenseItem}[collection_name]
    while len(collection) <= idx:
        collection.append(item_type())
    setattr(collection[idx], subfield, round_decimal(value) if subfield == "amount" else value)
    if collection_name == "attendance" and subfield in ["entry_time", "exit_time", "status"]:
        item = collection[idx]
        item.duration_hours = calculate_work_duration(item.entry_time, item.exit_time, item.status)


def _update_summary(form: FinancialFormData, subfield: str, value: Any) -> None:
    if subfield == "handwritten_current_balance" and (value is None or value == ""):
        form.summary.handwritten_current_balance = None
    else:
        setattr(form.summary, subfield, round_decimal(value))


@router.get("/documents/{document_id}/form", response_model=APIResponse[FinancialFormData])
async def get_digital_form(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_digital_form_impl(document_id, current_user, db)
exec('async def _get_digital_form_impl(\n    document_id: str,\n    current_user: User = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db),\n):\n    """Retrieves digital financial form data for the document."""\n    doc_res = await db.execute(\n        select(Document).where(Document.id == document_id, Document.user_id == current_user.id)\n    )\n    doc = doc_res.scalars().first()\n    if not doc:\n        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستند غير موجود.")\n    rec_res = await db.execute(\n        select(FinancialRecord).where(FinancialRecord.document_id == document_id)\n    )\n    record = rec_res.scalars().first()\n    if not record or not record.form_data:\n        from backend.app.utils.date_utils import get_current_amman_date, get_arabic_weekday\n        today = get_current_amman_date()\n        empty_form = FinancialFormData(\n            form_date=today.strftime("%Y-%m-%d"),\n            day_of_week=get_arabic_weekday(today),\n            attendance=[EmployeeAttendanceItem() for _ in range(settings.EMPLOYEES_ROW_COUNT)],\n            purchases=[PurchaseItem() for _ in range(settings.PURCHASES_ROW_COUNT)],\n            expenses=[ExpenseItem() for _ in range(settings.EXPENSES_ROW_COUNT)],\n        )\n        empty_form = recalculate_financial_form(empty_form)\n        record = FinancialRecord(\n            document_id=document_id,\n            user_id=current_user.id,\n            form_date=empty_form.form_date,\n            day_of_week=empty_form.day_of_week,\n            form_data=empty_form.model_dump(mode="json"),\n            total_sales=0.0,\n            total_expenses=0.0,\n            total_purchases=0.0,\n            current_balance=0.0,\n        )\n        db.add(record)\n        await db.commit()\n        await db.refresh(record)\n    form = FinancialFormData.model_validate(record.form_data)\n    form = recalculate_financial_form(form)\n    return APIResponse(success=True, data=form)\n', globals())


@router.put("/documents/{document_id}/form/field", response_model=APIResponse[FinancialFormData])
async def update_form_field(
    document_id: str,
    payload: FieldUpdatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _update_form_field_impl(document_id, payload, current_user, db)
exec('async def _update_form_field_impl(\n    document_id: str,\n    payload: FieldUpdatePayload,\n    current_user: User = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db),\n):\n    """\n    Updates a single field in the digital form and triggers immediate deterministic\n    recalculation of all 8 formulas and mismatch warnings.\n    """\n    rec_res = await db.execute(\n        select(FinancialRecord).where(\n            FinancialRecord.document_id == document_id, FinancialRecord.user_id == current_user.id\n        )\n    )\n    record = rec_res.scalars().first()\n    if not record:\n        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="سجل النموذج المالي غير موجود.")\n    if record.locked:\n        raise HTTPException(\n            status_code=status.HTTP_400_BAD_REQUEST,\n            detail="لا يمكن تعديل هذا النموذج لأنه معتمد ومغلق بشكل غير قابل للتعديل.",\n        )\n    form = FinancialFormData.model_validate(record.form_data)\n    updated_form = _apply_nested_field_update(form, payload.field_path, payload.value)\n    record.form_date = updated_form.form_date\n    record.day_of_week = updated_form.day_of_week\n    record.form_data = updated_form.model_dump(mode="json")\n    record.total_sales = float(updated_form.sales.total_sale)\n    record.total_expenses = float(updated_form.summary.total_expenses)\n    record.total_purchases = float(updated_form.summary.total_purchases)\n    record.current_balance = float(updated_form.summary.current_balance)\n    record.is_mathematically_valid = updated_form.is_mathematically_valid\n    await db.commit()\n    return APIResponse(success=True, message="تم تحديث الحقل وإعادة الحساب بنجاح.", data=updated_form)\n', globals())


@router.post("/documents/{document_id}/form/resolve-uncertainty", response_model=APIResponse[FinancialFormData])
async def resolve_ocr_uncertainty(
    document_id: str,
    payload: ResolveUncertaintyPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolves an OCR uncertainty item by applying user confirmation."""
    rec_res = await db.execute(
        select(FinancialRecord).where(
            FinancialRecord.document_id == document_id, FinancialRecord.user_id == current_user.id
        )
    )
    record = rec_res.scalars().first()
    if not record or record.locked:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="السجل غير قابل للتعديل.")
    form = FinancialFormData.model_validate(record.form_data)
    for u in form.ocr_uncertainties:
        if u.field_path == payload.field_path:
            u.resolved = True
            break
    updated_form = _apply_nested_field_update(form, payload.field_path, payload.confirmed_value)
    updated_form.all_uncertainties_resolved = all(u.resolved for u in updated_form.ocr_uncertainties)
    record.form_data = updated_form.model_dump(mode="json")
    record.all_uncertainties_resolved = updated_form.all_uncertainties_resolved
    await db.commit()
    return APIResponse(success=True, message="تم اعتماد وتأكيد القيمة بنجاح.", data=updated_form)


@router.post("/documents/{document_id}/approve", response_model=APIResponse[Any])
async def approve_financial_form(
    document_id: str,
    background_tasks: BackgroundTasks,
    payload: Optional[FormApprovalPayload] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _approve_financial_form_impl(document_id, background_tasks, payload, current_user, db)
exec('async def _approve_financial_form_impl(\n    document_id: str,\n    background_tasks: BackgroundTasks,\n    payload: Optional[FormApprovalPayload] = None,\n    current_user: User = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db),\n):\n    """\n    Final approval of the digitized financial form:\n    1. Replaces any previous approved record for the same calendar date.\n    2. Verifies mathematical consistency (or explicit override).\n    3. Generates printable Arabic RTL PDF.\n    4. Appends daily block with formulas to monthly Excel workbook.\n    5. Queues durable Microsoft Online sync if configured.\n    6. Automatically deletes temporary uploaded images from disk and verifies deletion.\n    """\n    doc_res = await db.execute(\n        select(Document).where(Document.id == document_id, Document.user_id == current_user.id)\n    )\n    doc = doc_res.scalars().first()\n    if not doc:\n        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستند غير موجود.")\n    rec_res = await db.execute(\n        select(FinancialRecord).where(FinancialRecord.document_id == document_id)\n    )\n    record = rec_res.scalars().first()\n    if not record:\n        from backend.app.utils.date_utils import get_current_amman_date, get_arabic_weekday\n        today = get_current_amman_date()\n        empty_form = FinancialFormData(\n            form_date=today.strftime("%Y-%m-%d"),\n            day_of_week=get_arabic_weekday(today),\n            attendance=[EmployeeAttendanceItem() for _ in range(settings.EMPLOYEES_ROW_COUNT)],\n            purchases=[PurchaseItem() for _ in range(settings.PURCHASES_ROW_COUNT)],\n            expenses=[ExpenseItem() for _ in range(settings.EXPENSES_ROW_COUNT)],\n        )\n        empty_form = recalculate_financial_form(empty_form)\n        record = FinancialRecord(\n            document_id=document_id,\n            user_id=current_user.id,\n            form_date=empty_form.form_date,\n            day_of_week=empty_form.day_of_week,\n            form_data=empty_form.model_dump(mode="json"),\n            total_sales=0.0,\n            total_expenses=0.0,\n            total_purchases=0.0,\n            current_balance=0.0,\n        )\n        db.add(record)\n        await db.flush()\n    if record.locked and record.is_approved:\n        return APIResponse(\n            success=True,\n            message="هذا النموذج معتمد مسبقاً بالفعل.",\n            data={"record_id": record.id, "form_date": record.form_date, "pdf_path": record.pdf_path},\n        )\n    form = FinancialFormData.model_validate(record.form_data)\n    form = recalculate_financial_form(form)\n    existing_approved_res = await db.execute(\n        select(FinancialRecord).where(\n            FinancialRecord.form_date == form.form_date,\n            FinancialRecord.is_approved == True,\n            FinancialRecord.user_id == current_user.id,\n            FinancialRecord.id != record.id,\n        )\n    )\n    conflicting_records = existing_approved_res.scalars().all()\n    for conflicting_record in conflicting_records:\n        old_document = None\n        if conflicting_record.document_id and conflicting_record.document_id != doc.id:\n            old_document_res = await db.execute(\n                select(Document).where(Document.id == conflicting_record.document_id)\n            )\n            old_document = old_document_res.scalars().first()\n        await db.delete(conflicting_record)\n        if old_document:\n            old_upload_dir = (\n                os.path.dirname(old_document.file_path)\n                if old_document.file_path\n                else None\n            )\n            old_processed_dir = os.path.join(\n                settings.STORAGE_DIR, "processed", old_document.id\n            )\n            if old_upload_dir and os.path.isdir(old_upload_dir):\n                shutil.rmtree(old_upload_dir, ignore_errors=True)\n            if os.path.isdir(old_processed_dir):\n                shutil.rmtree(old_processed_dir, ignore_errors=True)\n            await db.delete(old_document)\n        logger.info(\n            "Replaced previously approved financial record %s for date %s with %s.",\n            conflicting_record.id,\n            form.form_date,\n            record.id,\n        )\n    force_override = payload.force_override_mismatches if payload else False\n    if not form.is_mathematically_valid and not force_override:\n        raise HTTPException(\n            status_code=status.HTTP_400_BAD_REQUEST,\n            detail=(\n                "يوجد فروقات حسابية بين القيم المستخرجة والمجاميع المحسوبة. "\n                "يرجى تصحيح الفروقات أو تأكيد الاعتماد بالتجاوز الصريح."\n            ),\n        )\n    reports_dir = os.path.join(settings.STORAGE_DIR, "reports")\n    os.makedirs(reports_dir, exist_ok=True)\n    pdf_filename = f"AYA_{form.form_date}_{record.id[:8]}.pdf"\n    pdf_path = os.path.join(reports_dir, pdf_filename)\n    generate_financial_form_pdf(form, pdf_path)\n    record.pdf_path = pdf_path\n    monthly_exports_dir = os.path.join(settings.STORAGE_DIR, "exports")\n    os.makedirs(monthly_exports_dir, exist_ok=True)\n    month_prefix = form.form_date[:7]  # YYYY-MM\n    excel_path = os.path.join(monthly_exports_dir, f"AYA_Monthly_{month_prefix}.xlsx")\n    excel_sync_status = "unconfigured"\n    try:\n        append_daily_block_to_workbook(excel_path, form)\n        excel_sync_status = "synced_local"\n    except Exception as ee:\n        logger.error(f"Error appending daily block to local Excel: {ee}")\n    record.is_approved = True\n    record.locked = True\n    record.approved_at = datetime.now(timezone.utc)\n    record.approved_by = current_user.id\n    record.approval_notes = payload.notes if payload else None\n    record.excel_sync_status = excel_sync_status\n    record.form_data = form.model_dump(mode="json")\n    google_job = await GoogleSyncManager.create_or_get_sync_job(db, record)\n    deleted_files = []\n    upload_dir = os.path.join(settings.STORAGE_DIR, "uploads", doc.id)\n    processed_dir = os.path.join(settings.STORAGE_DIR, "processed", doc.id)\n    if os.path.exists(upload_dir):\n        shutil.rmtree(upload_dir, ignore_errors=True)\n        deleted_files.append("uploads")\n    if os.path.exists(processed_dir):\n        shutil.rmtree(processed_dir, ignore_errors=True)\n        deleted_files.append("processed")\n    uploads_still_exist = os.path.exists(upload_dir) or os.path.exists(processed_dir)\n    logger.info(\n        f"Approval cleanup for doc {doc.id}: upload_dir_deleted={not uploads_still_exist}"\n    )\n    doc.status = "approved"\n    doc.file_path = ""  # Cleared on disk after approval\n    audit = AuditLog(\n        user_id=current_user.id,\n        action="approve_financial_form",\n        resource_type="financial_record",\n        resource_id=record.id,\n        details={\n            "form_date": form.form_date,\n            "total_sales": float(form.sales.total_sale),\n            "current_balance": float(form.summary.current_balance),\n            "temporary_images_deleted": not uploads_still_exist,\n            "excel_path": excel_path,\n            "pdf_path": pdf_path,\n            "google_job_id": google_job.id,\n        },\n    )\n    db.add(audit)\n    await db.commit()\n    google_sync_result = None\n    try:\n        google_sync_result = await GoogleSyncManager.execute_sync_job(db, google_job.id)\n    except Exception as exc:\n        logger.error(f"Error during approval Google sync: {exc}")\n        google_sync_result = {"success": False, "error": str(exc)}\n    sheet_url = None\n    if isinstance(google_sync_result, dict):\n        sheet_url = google_sync_result.get("details", {}).get("sheet_url")\n    return APIResponse(\n        success=True,\n        message=f"تم اعتماد نموذج يوم {form.day_of_week} ({form.form_date}) بنجاح وتم حفظ السجل وحذف الصور المؤقتة والمزامنة مع Google Sheets.",\n        data={\n            "approved": True,\n            "record_id": record.id,\n            "pdf_path": pdf_path,\n            "google_sync": google_sync_result,\n            "sheet_url": sheet_url,\n        },\n    )\n', globals())


@router.get("/documents/{document_id}/pdf")
async def download_form_pdf(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _download_form_pdf_impl(document_id, current_user, db)
exec('async def _download_form_pdf_impl(\n    document_id: str,\n    current_user: User = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db),\n):\n    """Download the official Arabic RTL PDF for the financial form."""\n    rec_res = await db.execute(\n        select(FinancialRecord).where(\n            FinancialRecord.document_id == document_id, FinancialRecord.user_id == current_user.id\n        )\n    )\n    record = rec_res.scalars().first()\n    if not record:\n        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="السجل المالي غير موجود.")\n    if record.pdf_path and os.path.exists(record.pdf_path):\n        return FileResponse(\n            record.pdf_path,\n            media_type="application/pdf",\n            filename=f"AYA_Report_{record.form_date}.pdf",\n        )\n    reports_dir = os.path.join(settings.STORAGE_DIR, "reports")\n    os.makedirs(reports_dir, exist_ok=True)\n    pdf_path = os.path.join(reports_dir, f"AYA_{record.form_date}_{record.id[:8]}.pdf")\n    generate_financial_form_pdf(record.form_data, pdf_path)\n    record.pdf_path = pdf_path\n    await db.commit()\n    return FileResponse(\n        pdf_path,\n        media_type="application/pdf",\n        filename=f"AYA_Report_{record.form_date}.pdf",\n    )\n', globals())


@router.get("/financial-records", response_model=APIResponse[dict])
async def list_financial_records(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    weekday: Optional[str] = None,
    approved_only: bool = True,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _list_financial_records_impl(start_date, end_date, weekday, approved_only, limit, current_user, db)
exec('async def _list_financial_records_impl(\n    start_date: Optional[str] = None,\n    end_date: Optional[str] = None,\n    weekday: Optional[str] = None,\n    approved_only: bool = True,\n    limit: int = 50,\n    current_user: User = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db),\n):\n    """List historical financial records with filtering for Dashboard and History pages."""\n    query = select(FinancialRecord).where(FinancialRecord.user_id == current_user.id)\n    if approved_only:\n        query = query.where(FinancialRecord.is_approved == True)\n    if start_date:\n        query = query.where(FinancialRecord.form_date >= start_date)\n    if end_date:\n        query = query.where(FinancialRecord.form_date <= end_date)\n    if weekday:\n        query = query.where(FinancialRecord.day_of_week == weekday)\n    query = query.order_by(desc(FinancialRecord.form_date)).limit(limit)\n    res = await db.execute(query)\n    records = res.scalars().all()\n    items = []\n    total_sales_sum = Decimal("0.00")\n    total_expenses_sum = Decimal("0.00")\n    total_purchases_sum = Decimal("0.00")\n    for r in records:\n        sales_dec = Decimal(str(r.total_sales or 0)).quantize(Decimal("0.01"))\n        exp_dec = Decimal(str(r.total_expenses or 0)).quantize(Decimal("0.01"))\n        purch_dec = Decimal(str(r.total_purchases or 0)).quantize(Decimal("0.01"))\n        bal_dec = Decimal(str(r.current_balance or 0)).quantize(Decimal("0.01"))\n        total_sales_sum += sales_dec\n        total_expenses_sum += exp_dec\n        total_purchases_sum += purch_dec\n        items.append({\n            "id": r.id,\n            "document_id": r.document_id,\n            "form_date": r.form_date,\n            "day_of_week": r.day_of_week,\n            "total_sales": str(sales_dec),\n            "total_expenses": str(exp_dec),\n            "total_purchases": str(purch_dec),\n            "current_balance": str(bal_dec),\n            "is_approved": r.is_approved,\n            "approved_at": r.approved_at.isoformat() if r.approved_at else None,\n            "excel_sync_status": r.excel_sync_status,\n            "google_sync_status": r.google_sync_status,\n            "google_synced_at": r.google_synced_at.isoformat() if r.google_synced_at else None,\n            "pdf_url": f"/api/v1/documents/{r.document_id}/pdf" if r.document_id else None,\n        })\n    return APIResponse(\n        success=True,\n        data={\n            "records": items,\n            "kpi_summary": {\n                "count": len(items),\n                "total_sales_sum": str(total_sales_sum),\n                "total_expenses_sum": str(total_expenses_sum),\n                "total_purchases_sum": str(total_purchases_sum),\n                "currency": "JOD",\n            },\n        },\n    )\n', globals())


@router.get("/financial-records/{record_id}", response_model=APIResponse[dict])
async def get_financial_record_detail(
    record_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve complete read-only details of an approved financial record."""
    res = await db.execute(
        select(FinancialRecord).where(
            FinancialRecord.id == record_id, FinancialRecord.user_id == current_user.id
        )
    )
    record = res.scalars().first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="السجل المالي غير موجود.")
    return APIResponse(
        success=True,
        data={
            "id": record.id,
            "document_id": record.document_id,
            "form_date": record.form_date,
            "day_of_week": record.day_of_week,
            "form_data": record.form_data,
            "is_approved": record.is_approved,
            "approved_at": record.approved_at.isoformat() if record.approved_at else None,
            "excel_sync_status": record.excel_sync_status,
            "google_sync_status": record.google_sync_status,
            "google_synced_at": record.google_synced_at.isoformat() if record.google_synced_at else None,
            "pdf_url": f"/api/v1/documents/{record.document_id}/pdf" if record.document_id else None,
        },
    )
