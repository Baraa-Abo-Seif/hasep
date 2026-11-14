"""
Asynchronous pipeline orchestrating:
- Image Preprocessing → Gemini Vision Extraction → Deterministic Financial Calculation → Review Readiness.
"""

import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.database.session import AsyncSessionLocal
from backend.app.models.document import Document, DocumentPage, ProcessingJob
from backend.app.models.financial_record import FinancialRecord
from backend.app.image_processing.preprocessor import ImagePreprocessor
from backend.app.ai.gemini_provider import GeminiFinancialFormExtractor

logger = logging.getLogger(__name__)

# Public entry point used by FastAPI background task
async def run_document_processing_pipeline(document_id: str, user_instructions: str = "") -> None:
    await _run_document_processing_pipeline_impl(document_id, user_instructions)

# ---------------------------------------------------------------------------
# Implementation – deliberately kept out of the exec‑string to make it edit‑
# friendly. The function mirrors the previous behaviour but now processes **all**
# pages concurrently (limited by settings.MAX_CONCURRENCY).
# ---------------------------------------------------------------------------
async def _run_document_processing_pipeline_impl(document_id: str, user_instructions: str = "") -> None:
    async with AsyncSessionLocal() as db:
        # -------------------------------------------------------------------
        # 1️⃣ Load document and create / fetch processing job record
        # -------------------------------------------------------------------
        doc_res = await db.execute(select(Document).where(Document.id == document_id))
        doc = doc_res.scalars().first()
        if not doc:
            logger.error(f"Pipeline error: Document {document_id} not found.")
            return

        job_res = await db.execute(
            select(ProcessingJob)
            .where(ProcessingJob.document_id == document_id)
            .order_by(ProcessingJob.created_at.desc())
        )
        job = job_res.scalars().first()
        if not job:
            job = ProcessingJob(document_id=document_id, job_type="full_pipeline")
            db.add(job)

        try:
            # -------------------------------------------------------------------
            # 2️⃣ Update DB status to "processing"
            # -------------------------------------------------------------------
            doc.status = "processing"
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            job.progress_percentage = 15
            job.stage_description = "بدء معالجة وتحسين صورة النموذج المالي"
            await db.commit()

            # -------------------------------------------------------------------
            # 3️⃣ Fetch **all** pages for the document
            # -------------------------------------------------------------------
            page_res = await db.execute(select(DocumentPage).where(DocumentPage.document_id == document_id))
            pages: List[DocumentPage] = page_res.scalars().all()
            if not pages:
                raise ValueError("No pages found for document.")

            # Create a directory for any temporary artefacts (enhanced images, PDFs …)
            processed_dir = os.path.join(settings.STORAGE_DIR, "processed", document_id)
            os.makedirs(processed_dir, exist_ok=True)

            # Initialise Gemini extractor once – creating a client per page is wasteful
            extractor = GeminiFinancialFormExtractor()

            # Optional fast‑mode: skip expensive image preprocessing when user wants speed
            fast_mode: bool = getattr(settings, "FAST_MODE", False)
            semaphore = asyncio.Semaphore(settings.MAX_CONCURRENCY or 4)

            async def _process_page(page: DocumentPage) -> None:
                async with semaphore:
                    # -----------------------------------------------------------
                    # a) Determine which image the extractor should consume
                    # -----------------------------------------------------------
                    input_image_path = page.image_path
                    if not fast_mode:
                        enhanced_path = os.path.join(processed_dir, f"enhanced_{page.id}.jpg")
                        try:
                            prep_info = ImagePreprocessor.preprocess_for_ocr(page.image_path, enhanced_path)
                            page.preprocessing_applied = prep_info
                            input_image_path = enhanced_path
                        except Exception as exc:  # pragma: no cover – logging only
                            logger.warning(f"Preprocessing warning for page {page.id}: {exc}")

                    # -----------------------------------------------------------
                    # b) Handle PDFs – render first page to JPEG for Gemini
                    # -----------------------------------------------------------
                    if input_image_path.lower().endswith('.pdf'):
                        import pypdfium2 as pdfium
                        pdf = pdfium.PdfDocument(input_image_path)
                        if len(pdf) == 0:
                            raise ValueError("ملف PDF المرفوع فارغ ولا يحتوي على أي صفحات.")
                        rendered_path = os.path.join(processed_dir, f"rendered_{page.id}.jpg")
                        pdf[0].render(scale=2.0).to_pil().save(rendered_path, "JPEG", quality=95)
                        input_image_path = rendered_path

                    # -----------------------------------------------------------
                    # c) Determine MIME type for Gemini request
                    # -----------------------------------------------------------
                    mime_type = "image/jpeg"
                    if input_image_path.lower().endswith('.png'):
                        mime_type = "image/png"
                    elif input_image_path.lower().endswith('.webp'):
                        mime_type = "image/webp"

                    # -----------------------------------------------------------
                    # d) Read bytes and invoke Gemini
                    # -----------------------------------------------------------
                    with open(input_image_path, "rb") as f:
                        image_bytes = f.read()
                    financial_form = await extractor.extract_from_image_bytes(image_bytes, mime_type)

                    # -----------------------------------------------------------
                    # e) Persist (or update) a FinancialRecord for **this** document
                    # -----------------------------------------------------------
                    rec_res = await db.execute(select(FinancialRecord).where(FinancialRecord.document_id == document_id))
                    record = rec_res.scalars().first()
                    form_json = financial_form.model_dump(mode="json")

                    if not record:
                        record = FinancialRecord(
                            document_id=document_id,
                            user_id=doc.user_id,
                            form_date=financial_form.form_date,
                            day_of_week=financial_form.day_of_week,
                            form_data=form_json,
                            total_sales=float(financial_form.sales.total_sale),
                            total_expenses=float(financial_form.summary.total_expenses),
                            total_purchases=float(financial_form.summary.total_purchases),
                            current_balance=float(financial_form.summary.current_balance),
                            is_mathematically_valid=financial_form.is_mathematically_valid,
                            all_uncertainties_resolved=financial_form.all_uncertainties_resolved,
                        )
                        db.add(record)
                    else:
                        record.form_date = financial_form.form_date
                        record.day_of_week = financial_form.day_of_week
                        record.form_data = form_json
                        record.total_sales = float(financial_form.sales.total_sale)
                        record.total_expenses = float(financial_form.summary.total_expenses)
                        record.total_purchases = float(financial_form.summary.total_purchases)
                        record.current_balance = float(financial_form.summary.current_balance)
                        record.is_mathematically_valid = financial_form.is_mathematically_valid
                        record.all_uncertainties_resolved = financial_form.all_uncertainties_resolved

                    # Commit per‑page so that progress is visible even if later pages fail
                    await db.commit()

            # -------------------------------------------------------------------
            # 4️⃣ Run all page tasks concurrently (bounded by semaphore)
            # -------------------------------------------------------------------
            await asyncio.gather(*( _process_page(p) for p in pages ))

            # -------------------------------------------------------------------
            # 5️⃣ Finalise job / document status after **all** pages succeeded
            # -------------------------------------------------------------------
            doc.document_type = "financial_form"
            doc.status = "ready_for_review"
            doc.error_message = None

            job.status = "completed"
            job.progress_percentage = 100
            job.stage_description = "اكتملت المعالجة بنجاح. النموذج جاهز للمراجعة الرقمية والاعتماد."
            job.error_details = None
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info(f"Project # hasep Pipeline successfully processed document {document_id}")

        except Exception as exc:  # pragma: no cover – ensures DB consistency on failure
            logger.exception(f"Pipeline error for document {document_id}: {exc}")
            await db.rollback()
            if doc:
                doc.status = "failed"
                doc.error_message = str(exc)
            if job:
                job.status = "failed"
                job.error_details = str(exc)
                job.stage_description = f"فشلت المعالجة: {exc}"
            await db.commit()
