from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from backend.app.schemas.ocr import BoundingBox


class ExtractedCellData(BaseModel):
    value: Optional[Union[str, float, int, bool]] = None
    original_text: Optional[str] = None
    data_type: str = "string"  # 'string', 'number', 'decimal', 'date', 'currency', 'boolean'
    confidence: Optional[float] = None
    needs_review: bool = False
    uncertainty_reason: Optional[str] = None
    bounding_box: Optional[BoundingBox] = None


class ExtractedRowData(BaseModel):
    row_number: int
    row_id: Optional[str] = None
    values: Dict[str, ExtractedCellData]  # column_key -> ExtractedCellData


class ExtractedColumnData(BaseModel):
    key: str
    label: str
    data_type: str = "string"
    order_index: int = 0
    is_required: bool = False


class ExtractedTableData(BaseModel):
    table_id: str
    title: str = "الجدول المستخرج"
    description: Optional[str] = None
    confidence_score: Optional[float] = None
    page_number: int = 1
    columns: List[ExtractedColumnData] = Field(default_factory=list)
    rows: List[ExtractedRowData] = Field(default_factory=list)


class ValidationErrorData(BaseModel):
    table_id: Optional[str] = None
    row_number: Optional[int] = None
    column_key: Optional[str] = None
    validation_type: str  # missing_required, invalid_type, duplicate_row, ambiguous_value
    severity: str = "warning"  # error, warning, info
    message: str


class DocumentExtractionResult(BaseModel):
    document_id: str
    document_type: str = "other"  # general_document, invoice, receipt, student_list, attendance_sheet, financial_statement, table, other
    language: str = "ar"
    confidence_score: float = 1.0
    summary: Optional[str] = None
    tables: List[ExtractedTableData] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    validation_errors: List[ValidationErrorData] = Field(default_factory=list)
