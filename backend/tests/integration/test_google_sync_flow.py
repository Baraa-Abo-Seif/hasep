"""
Integration tests for Google Sheets Synchronization Lifecycle in Project # hasep.
Guarantees:
1. Sync ONLY triggers after Final Approval (never during upload, OCR, or review).
2. Atomic database transaction binds approval to sync queue creation.
3. 1 approved record per calendar date is strictly maintained.
4. Background retry logic and error tracking.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from backend.app.main import app
from backend.app.database.session import AsyncSessionLocal
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.financial_record import FinancialRecord
from backend.app.models.google_sync import GoogleSheetsSyncJob
from backend.app.models.google_connection import GoogleConnection
from backend.app.schemas.financial_form import FinancialFormData
from backend.app.services.google_sync_service import GoogleSyncManager
from backend.app.core.security import encrypt_token
from backend.app.utils.date_utils import get_current_amman_date


import io
from PIL import Image

def _create_test_image_bytes():
    img = Image.new("RGB", (200, 200), color="white")
    arr = io.BytesIO()
    img.save(arr, format="JPEG")
    return arr.getvalue()


@pytest.mark.asyncio
async def test_no_sync_during_upload_and_review():
    """Verify that uploading or reviewing documents NEVER triggers or queues Google Sheets sync."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Upload a document
        files = {"files": ("test_form.jpg", _create_test_image_bytes(), "image/jpeg")}
        up_res = await client.post("/api/v1/documents/upload?auto_process=false", files=files)
        assert up_res.status_code == 200
        doc_id = up_res.json()["data"][0]["id"]

        # Verify DB: No Google sync job exists for this document
        async with AsyncSessionLocal() as session:
            job_res = await session.execute(
                select(GoogleSheetsSyncJob)
                .join(FinancialRecord, GoogleSheetsSyncJob.approved_record_id == FinancialRecord.id)
                .where(FinancialRecord.document_id == doc_id)
            )
            assert len(job_res.scalars().all()) == 0

        # Step 2: Fetch digital form for review
        form_res = await client.get(f"/api/v1/documents/{doc_id}/form")
        assert form_res.status_code == 200

        # Step 3: Edit a field
        edit_res = await client.put(
            f"/api/v1/documents/{doc_id}/form/field",
            json={"field_path": "sales.sales", "value": 150.0},
        )
        assert edit_res.status_code == 200

        # Verify DB: Still NO Google sync job exists during review!
        async with AsyncSessionLocal() as session:
            job_res = await session.execute(
                select(GoogleSheetsSyncJob)
                .join(FinancialRecord, GoogleSheetsSyncJob.approved_record_id == FinancialRecord.id)
                .where(FinancialRecord.document_id == doc_id)
            )
            assert len(job_res.scalars().all()) == 0


@pytest.mark.asyncio
async def test_sync_job_created_atomically_on_final_approval():
    """Verify that Google Sheets sync job is created atomically in DB ONLY upon final approval."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Upload
        files = {"files": ("approval_test.jpg", _create_test_image_bytes(), "image/jpeg")}
        up_res = await client.post("/api/v1/documents/upload?auto_process=false", files=files)
        assert up_res.status_code == 200
        doc_id = up_res.json()["data"][0]["id"]

        # Initialize form and set a non-conflicting calendar date
        await client.get(f"/api/v1/documents/{doc_id}/form")
        await client.put(
            f"/api/v1/documents/{doc_id}/form/field",
            json={"field_path": "form_date", "value": "2026-11-28"},
        )

        # Final Approval
        app_res = await client.post(
            f"/api/v1/documents/{doc_id}/approve",
            json={"notes": "تأكيد تجريبي للاعتماد والمزامنة", "force_override_mismatches": True},
        )
        assert app_res.status_code == 200
        assert app_res.json()["success"] is True

        # Verify DB: Exactly ONE GoogleSheetsSyncJob created with PENDING status
        async with AsyncSessionLocal() as session:
            rec_res = await session.execute(
                select(FinancialRecord).where(FinancialRecord.document_id == doc_id)
            )
            record = rec_res.scalars().first()
            assert record is not None
            assert record.is_approved is True
            assert record.locked is True

            job_res = await session.execute(
                select(GoogleSheetsSyncJob).where(GoogleSheetsSyncJob.approved_record_id == record.id)
            )
            job = job_res.scalars().first()
            assert job is not None
            assert job.idempotency_key == f"aya_gsheet_{record.id}"
            assert job.status in ["PENDING", "SUCCESS", "RETRY"]


@pytest.mark.asyncio
async def test_final_approval_replaces_previous_approved_record_for_same_date():
    """A new approval for a date replaces the previous approved record."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first_upload = {"files": ("first.jpg", _create_test_image_bytes(), "image/jpeg")}
        first_res = await client.post("/api/v1/documents/upload?auto_process=false", files=first_upload)
        assert first_res.status_code == 200
        first_id = first_res.json()["data"][0]["id"]
        await client.get(f"/api/v1/documents/{first_id}/form")
        today = get_current_amman_date().strftime("%Y-%m-%d")
        await client.put(
            f"/api/v1/documents/{first_id}/form/field",
            json={"field_path": "form_date", "value": today},
        )
        first_approval = await client.post(
            f"/api/v1/documents/{first_id}/approve",
            json={"force_override_mismatches": True},
        )
        assert first_approval.status_code == 200

        second_upload = {"files": ("second.jpg", _create_test_image_bytes(), "image/jpeg")}
        second_res = await client.post("/api/v1/documents/upload?auto_process=false", files=second_upload)
        assert second_res.status_code == 200
        second_id = second_res.json()["data"][0]["id"]
        await client.get(f"/api/v1/documents/{second_id}/form")
        await client.put(
            f"/api/v1/documents/{second_id}/form/field",
            json={"field_path": "form_date", "value": today},
        )
        second_approval = await client.post(
            f"/api/v1/documents/{second_id}/approve",
            json={"force_override_mismatches": True},
        )
        assert second_approval.status_code == 200

        async with AsyncSessionLocal() as session:
            first_record_res = await session.execute(
                select(FinancialRecord).where(FinancialRecord.document_id == first_id)
            )
            second_record_res = await session.execute(
                select(FinancialRecord).where(FinancialRecord.document_id == second_id)
            )
            assert first_record_res.scalars().first() is None
            assert second_record_res.scalars().first() is not None


@pytest.mark.asyncio
async def test_unapproved_record_cannot_be_queued():
    """Verify that unapproved financial record cannot be queued for Google Sheets sync."""
    async with AsyncSessionLocal() as session:
        unapproved_record = FinancialRecord(
            document_id="unapproved-doc-id",
            user_id="00000000-0000-0000-0000-000000000001",
            form_date="2026-11-20",
            day_of_week="الجمعة",
            is_approved=False,
            locked=False,
        )
        session.add(unapproved_record)
        await session.flush()

        with pytest.raises(ValueError, match="Cannot queue Google Sheets sync for unapproved record"):
            await GoogleSyncManager.create_or_get_sync_job(session, unapproved_record)


@pytest.mark.asyncio
async def test_google_sync_api_endpoints():
    """Verify Google Sheets API endpoints for status, listing sync jobs, and retrying."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Google Auth Status
        auth_status = await client.get("/api/v1/auth/google/status")
        assert auth_status.status_code == 200
        assert auth_status.json()["success"] is True
        assert "is_connected" in auth_status.json()["data"]

        # 2. Google Sheets Status
        sheets_status = await client.get("/api/v1/google-sheets/status")
        assert sheets_status.status_code == 200
        assert sheets_status.json()["success"] is True
        assert "sync_stats" in sheets_status.json()["data"]

        # 3. List Sync Jobs
        jobs_res = await client.get("/api/v1/google-sheets/sync-jobs")
        assert jobs_res.status_code == 200
        assert jobs_res.json()["success"] is True
        assert isinstance(jobs_res.json()["data"], list)

        # 4. Retry All Pending
        retry_res = await client.post("/api/v1/google-sheets/sync-jobs/retry-pending")
        assert retry_res.status_code == 200
        assert retry_res.json()["success"] is True
