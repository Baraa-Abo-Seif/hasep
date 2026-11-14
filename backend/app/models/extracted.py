import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, JSON, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.session import Base


class ExtractedTable(Base):
    __tablename__ = "extracted_tables"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    table_index: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(255), default="جدول مستخرج")
    description: Mapped[str] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)
    page_number: Mapped[int] = mapped_column(Integer, default=1)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    document: Mapped["Document"] = relationship("Document", back_populates="tables")
    columns: Mapped[list["ExtractedColumn"]] = relationship("ExtractedColumn", back_populates="table", cascade="all, delete-orphan", order_by="ExtractedColumn.order_index")
    rows: Mapped[list["ExtractedRow"]] = relationship("ExtractedRow", back_populates="table", cascade="all, delete-orphan", order_by="ExtractedRow.row_number")


class ExtractedColumn(Base):
    __tablename__ = "extracted_columns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    table_id: Mapped[str] = mapped_column(String(36), ForeignKey("extracted_tables.id", ondelete="CASCADE"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False)  # identifier e.g. "product_name"
    label: Mapped[str] = mapped_column(String(255), nullable=False)  # display title e.g. "اسم المنتج"
    data_type: Mapped[str] = mapped_column(String(50), default="string")  # string, number, decimal, date, currency, boolean
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    
    table: Mapped["ExtractedTable"] = relationship("ExtractedTable", back_populates="columns")
    cells: Mapped[list["ExtractedCell"]] = relationship("ExtractedCell", back_populates="column", cascade="all, delete-orphan")


class ExtractedRow(Base):
    __tablename__ = "extracted_rows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    table_id: Mapped[str] = mapped_column(String(36), ForeignKey("extracted_tables.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    
    table: Mapped["ExtractedTable"] = relationship("ExtractedTable", back_populates="rows")
    cells: Mapped[list["ExtractedCell"]] = relationship("ExtractedCell", back_populates="row", cascade="all, delete-orphan")


class ExtractedCell(Base):
    __tablename__ = "extracted_cells"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    row_id: Mapped[str] = mapped_column(String(36), ForeignKey("extracted_rows.id", ondelete="CASCADE"), nullable=False, index=True)
    column_id: Mapped[str] = mapped_column(String(36), ForeignKey("extracted_columns.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Text values
    original_text: Mapped[str] = mapped_column(Text, nullable=True)  # Raw unnormalized OCR text
    normalized_value: Mapped[str] = mapped_column(Text, nullable=True)  # AI interpreted & typed value
    data_type: Mapped[str] = mapped_column(String(50), default="string")
    
    # Confidence and review flags
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    uncertainty_reason: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Coordinate binding to original image page: {"page": 1, "bbox": [x, y, w, h]}
    bbox_coordinates: Mapped[dict] = mapped_column(JSON, default=dict)

    row: Mapped["ExtractedRow"] = relationship("ExtractedRow", back_populates="cells")
    column: Mapped["ExtractedColumn"] = relationship("ExtractedColumn", back_populates="cells")
    corrections: Mapped[list["UserCorrection"]] = relationship("UserCorrection", back_populates="cell", cascade="all, delete-orphan")
