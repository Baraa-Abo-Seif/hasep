"""
Google Sheets Sync Queue & Job model for Project # hasep.
Guarantees durable, idempotent, retry-capable background synchronization
of approved financial forms to Google Sheets.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.session import Base


class GoogleSheetsSyncJob(Base):
    __tablename__ = "google_sheets_sync_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    approved_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("financial_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    spreadsheet_id: Mapped[str] = mapped_column(String(255), nullable=True)
    target_sheet_name: Mapped[str] = mapped_column(String(100), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(
        String(120), unique=True, index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default="PENDING", index=True
    )  # 'PENDING', 'PROCESSING', 'SUCCESS', 'RETRY', 'FAILED'
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=5)
    last_error: Mapped[str] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    financial_record: Mapped["FinancialRecord"] = relationship(
        "FinancialRecord", back_populates="google_sync_jobs"
    )

    __table_args__ = (
        UniqueConstraint("approved_record_id", name="uq_google_sync_approved_record"),
    )
