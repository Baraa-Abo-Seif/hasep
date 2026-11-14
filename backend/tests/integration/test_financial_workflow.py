"""
Integration test for Project # hasep complete financial workflow:
- Digital form review & live recalculation
- Approval logic & 1-approved-record-per-day rule
- Automatic deletion of temporary uploaded images from disk
- PDF report generation
- History query and KPI aggregations
"""

import os
import io
import pytest
import pytest_asyncio
import httpx
from PIL import Image
from sqlalchemy import delete

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.database.session import init_db, AsyncSessionLocal
from backend.app.models.financial_record import FinancialRecord
from backend.app.models.document import Document


@pytest_asyncio.fixture(autouse=True)
async def clean_database():
    await init_db()
    async with AsyncSessionLocal() as session:
        await session.execute(delete(FinancialRecord))
        await session.execute(delete(Document))
        await session.commit()
    yield


@pytest.mark.asyncio
async def test_complete_financial_workflow_and_one_per_day_enforcement():
    # 1. Create a dummy test image
    img = Image.new("RGB", (300, 400), color="white")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    img_bytes = img_byte_arr.getvalue()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # A. Upload first document
        files = {"files": ("daily_form_1.jpg", img_bytes, "image/jpeg")}
        up_res = await client.post("/api/v1/documents/upload?auto_process=false", files=files)
        assert up_res.status_code == 200
        doc1_id = up_res.json()["data"][0]["id"]

        # Check upload directory exists on disk
        upload_dir = os.path.join(settings.STORAGE_DIR, "uploads", doc1_id)
        assert os.path.exists(upload_dir)

        # B. Get digital form
        form_res = await client.get(f"/api/v1/documents/{doc1_id}/form")
        assert form_res.status_code == 200
        form_data = form_res.json()["data"]
        target_date = form_data["form_date"]

        # C. Update field: add purchase amount 50.00
        update_res = await client.put(
            f"/api/v1/documents/{doc1_id}/form/field",
            json={"field_path": "purchases.0.amount", "value": "50.00"}
        )
        assert update_res.status_code == 200
        updated_data = update_res.json()["data"]
        assert updated_data["summary"]["total_purchases"] == "50.00"

        # D. First approval succeeds
        app_res1 = await client.post(
            f"/api/v1/documents/{doc1_id}/approve",
            json={"notes": "First approval for today", "force_override_mismatches": True}
        )
        assert app_res1.json()["success"] is True
        assert app_res1.json()["data"]["approved"] is True

        # E. Verify temporary image directory has been physically deleted from disk!
        assert not os.path.exists(upload_dir), "Uploaded directory was NOT deleted after approval!"

        # F. Download generated PDF
        pdf_res = await client.get(f"/api/v1/documents/{doc1_id}/pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert len(pdf_res.content) > 500

        # G. Upload SECOND document and set same form_date
        files2 = {"files": ("daily_form_2.jpg", img_bytes, "image/jpeg")}
        up_res2 = await client.post("/api/v1/documents/upload?auto_process=false", files=files2)
        assert up_res2.status_code == 200
        doc2_id = up_res2.json()["data"][0]["id"]

        # Ensure doc2 has the exact same date
        await client.put(
            f"/api/v1/documents/{doc2_id}/form/field",
            json={"field_path": "form_date", "value": target_date}
        )

        # H. Attempt to approve second document for the SAME date -> MUST FAIL WITH 409 CONFLICT!
        app_res2 = await client.post(
            f"/api/v1/documents/{doc2_id}/approve",
            json={"notes": "Duplicate day approval attempt", "force_override_mismatches": True}
        )
        assert app_res2.status_code == 409
        assert "لا يمكن تسجيل أكثر من نموذج" in app_res2.json()["detail"]

        # I. Query history records & KPI
        hist_res = await client.get("/api/v1/financial-records")
        assert hist_res.status_code == 200
        hist_data = hist_res.json()["data"]
        assert len(hist_data["records"]) == 1
        assert hist_data["records"][0]["form_date"] == target_date
        assert hist_data["kpi_summary"]["currency"] == "JOD"
