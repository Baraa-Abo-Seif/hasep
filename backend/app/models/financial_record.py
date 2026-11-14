"""
Financial Record database model for Project # hasep.
Stores normalized daily financial forms, calculations, approvals, and sync status.
Stores the latest approved record for each calendar date.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Numeric,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.session import Base


class FinancialRecord(Base):
    __tablename__ = "financial_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Nullable document_id so the record stays intact when document/image is cleaned up!
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    form_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    day_of_week: Mapped[str] = mapped_column(String(20), nullable=False)

    # Full structured digital form data
    form_data: Mapped[dict] = mapped_column(JSON, default=dict)

    # Key aggregated metrics for fast dashboard queries and history filtering
    total_sales: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    total_expenses: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    total_purchases: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    current_balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)

    # Verification & Approval State
    is_mathematically_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    all_uncertainties_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str] = mapped_column(String(36), nullable=True)
    approval_notes: Mapped[str] = mapped_column(Text, nullable=True)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)  # Immutable once approved

    # Offline & Excel Sync
    excel_sync_status: Mapped[str] = mapped_column(
        String(50), default="unconfigured", index=True
    )  # 'unconfigured', 'pending', 'synced', 'failed'
    excel_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Google Sheets Sync
    google_sync_status: Mapped[str] = mapped_column(
        String(50), default="unconfigured", index=True
    )  # 'unconfigured', 'pending', 'synced', 'failed'
    google_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    pdf_path: Mapped[str] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship("User")
    google_sync_jobs: Mapped[list["GoogleSheetsSyncJob"]] = relationship(
        "GoogleSheetsSyncJob", back_populates="financial_record", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_form_date_approved", "form_date", "is_approved"),
    )
