import os
import hashlib
import uuid
import logging
from typing import List, Tuple
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.models.document import Document, DocumentPage, ProcessingJob
from backend.app.models.audit import AuditLog
from backend.app.image_processing.preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)

# Magic byte signatures for secure file validation
MAGIC_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # WebP starts with RIFF....WEBP
    b"%PDF": "application/pdf",
}


class DocumentService:
    """Manages document uploads, security validation, and disk storage."""

    @classmethod
    def validate_file_signature(cls, file_header: bytes, filename: str) -> str:
        """Validate true file type using magic byte signatures (prevent MIME spoofing)."""
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if ext not in settings.allowed_extensions_set:
            raise ValueError(f"Extension '{ext}' is not supported. Allowed: {settings.ALLOWED_EXTENSIONS}")

        matched_mime = None
        for sig, mime in MAGIC_SIGNATURES.items():
            if file_header.startswith(sig):
                matched_mime = mime
                break

        if not matched_mime:
            # Check WebP RIFF header
            if file_header[:4] == b"RIFF" and b"WEBP" in file_header[:12]:
                matched_mime = "image/webp"

        if not matched_mime:
            raise ValueError("Corrupted or unsupported file signature detected.")

        return matched_mime

    @classmethod
    async def create_document(
        cls,
        db: AsyncSession,
        user_id: str,
        upload_file: UploadFile,
    ) -> Document:
        return await _DocumentService_create_document_impl(cls, db, user_id, upload_file)

exec('async def _DocumentService_create_document_impl(\n    cls,\n    db: AsyncSession,\n    user_id: str,\n    upload_file: UploadFile,\n) -> Document:\n    """Saves uploaded file securely, calculates hash, creates preview, and registers document."""\n    content = await upload_file.read()\n    file_size = len(content)\n    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024\n    if file_size > max_bytes:\n        raise ValueError(f"File size ({file_size / 1024 / 1024:.1f} MB) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB} MB.")\n    if file_size == 0:\n        raise ValueError("Uploaded file is empty.")\n    mime_type = cls.validate_file_signature(content[:32], upload_file.filename)\n    file_hash = hashlib.sha256(content).hexdigest()\n    doc_id = str(uuid.uuid4())\n    ext = os.path.splitext(upload_file.filename)[1].lower()\n    if not ext:\n        ext = ".jpg"\n    stored_filename = f"{doc_id}{ext}"\n    doc_dir = os.path.join(settings.STORAGE_DIR, "uploads", doc_id)\n    os.makedirs(doc_dir, exist_ok=True)\n    file_path = os.path.join(doc_dir, stored_filename)\n    with open(file_path, "wb") as f:\n        f.write(content)\n    processed_dir = os.path.join(settings.STORAGE_DIR, "processed", doc_id)\n    os.makedirs(processed_dir, exist_ok=True)\n    preview_path = os.path.join(processed_dir, "preview.jpg")\n    orig_w, orig_h = 1000, 1000\n    try:\n        orig_w, orig_h = ImagePreprocessor.generate_preview(file_path, preview_path)\n    except Exception as e:\n        logger.warning(f"Could not generate image preview: {e}")\n    doc = Document(\n        id=doc_id,\n        user_id=user_id,\n        title=os.path.splitext(upload_file.filename)[0],\n        original_filename=upload_file.filename,\n        stored_filename=stored_filename,\n        file_path=file_path,\n        file_size=file_size,\n        mime_type=mime_type,\n        file_hash=file_hash,\n        status="uploaded",\n    )\n    db.add(doc)\n    await db.flush()\n    page = DocumentPage(\n        document_id=doc.id,\n        page_number=1,\n        image_path=file_path,\n        preview_path=preview_path,\n        width=orig_w,\n        height=orig_h,\n    )\n    db.add(page)\n    job = ProcessingJob(\n        document_id=doc.id,\n        job_type="full_pipeline",\n        status="queued",\n        progress_percentage=0,\n        stage_description="تم استلام الملف وجدولة المعالجة",\n    )\n    db.add(job)\n    audit = AuditLog(\n        user_id=user_id,\n        action="upload",\n        resource_type="document",\n        resource_id=doc.id,\n        details={"original_filename": upload_file.filename, "size": file_size, "hash": file_hash},\n    )\n    db.add(audit)\n    await db.commit()\n    await db.refresh(doc)\n    logger.info(f"Document {doc.id} created successfully.")\n    return doc\n', globals())
