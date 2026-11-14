import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.session import Base


class OCRResult(Base):
    __tablename__ = "ocr_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, default=1)
    provider: Mapped[str] = mapped_column(String(50), default="azure_doc_intelligence")  # 'azure_doc_intelligence', 'local_cv'
    model_used: Mapped[str] = mapped_column(String(100), nullable=True)  # 'prebuilt-layout', 'prebuilt-read'
    
    # Textual and structured representation
    raw_response_json: Mapped[dict] = mapped_column(JSON, default=dict)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    language_detected: Mapped[str] = mapped_column(String(20), default="ar")
    average_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    
    # Detailed geometry elements
    # lines_data: [{"text": str, "bounding_box": [x,y,w,h], "confidence": float, "words": [...]}]
    lines_data: Mapped[list] = mapped_column(JSON, default=list)
    # words_data: [{"text": str, "bounding_box": [x,y,w,h], "confidence": float, "is_handwritten": bool}]
    words_data: Mapped[list] = mapped_column(JSON, default=list)
    # raw_tables_data: detected grid/table structures directly from OCR layout
    tables_data: Mapped[list] = mapped_column(JSON, default=list)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    document: Mapped["Document"] = relationship("Document", back_populates="ocr_results")
