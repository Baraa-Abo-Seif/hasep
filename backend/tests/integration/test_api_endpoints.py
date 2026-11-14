import io
import pytest
import pytest_asyncio
import httpx
from PIL import Image

from backend.app.main import app
from backend.app.database.session import init_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await init_db()
    from backend.app.database.session import AsyncSessionLocal
    from backend.app.models.financial_record import FinancialRecord
    from sqlalchemy import delete
    async with AsyncSessionLocal() as session:
        await session.execute(delete(FinancialRecord))
        await session.commit()
    yield


@pytest.mark.asyncio
async def test_health_endpoints():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_auth_status_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/auth/status")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "user" in data


@pytest.mark.asyncio
async def test_document_upload_and_review_flow():
    # Create valid JPEG in memory
    img = Image.new("RGB", (200, 200), color="white")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    img_bytes = img_byte_arr.getvalue()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Upload document (auto_process=False for unit isolation)
        files = {"files": ("test_invoice.jpg", img_bytes, "image/jpeg")}
        upload_res = await client.post("/api/v1/documents/upload?auto_process=false", files=files)
        assert upload_res.status_code == 200
        upload_data = upload_res.json()["data"]
        assert len(upload_data) == 1
        doc_id = upload_data[0]["id"]

        # 2. List documents
        list_res = await client.get("/api/v1/documents")
        assert list_res.status_code == 200
        assert any(d["id"] == doc_id for d in list_res.json()["items"])

        # 3. Check status
        status_res = await client.get(f"/api/v1/documents/{doc_id}/status")
        assert status_res.status_code == 200
        assert status_res.json()["data"]["document_id"] == doc_id

        # 4. Approve document
        approve_res = await client.post(f"/api/v1/documents/{doc_id}/approve", json={"notes": "Approved for export"})
        assert approve_res.json()["success"] is True
        assert approve_res.json()["data"]["approved"] is True


@pytest.mark.asyncio
async def test_history_stats():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Check stats
        stats_res = await client.get("/api/v1/history/stats")
        assert stats_res.status_code == 200
        assert "total_documents" in stats_res.json()["data"]
