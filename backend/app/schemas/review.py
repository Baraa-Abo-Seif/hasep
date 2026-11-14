from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from backend.app.schemas.structured_data import ExtractedTableData, ValidationErrorData


class CellUpdateRequest(BaseModel):
    table_id: str
    row_id: str
    column_id: str
    new_value: Optional[Union[str, float, int, bool]] = None
    reason: Optional[str] = None


class ColumnUpdateRequest(BaseModel):
    table_id: str
    column_id: str
    label: Optional[str] = None
    data_type: Optional[str] = None
    order_index: Optional[int] = None


class AddRowRequest(BaseModel):
    table_id: str
    values: Dict[str, Any] = Field(default_factory=dict)


class AddColumnRequest(BaseModel):
    table_id: str
    key: str
    label: str
    data_type: str = "string"


class ReviewApprovalRequest(BaseModel):
    notes: Optional[str] = None


class ReviewRejectionRequest(BaseModel):
    reason: str


class DocumentReviewData(BaseModel):
    document_id: str
    document_title: str
    document_type: str
    status: str
    is_approved: bool
    tables: List[ExtractedTableData]
    validation_errors: List[ValidationErrorData]
    image_pages: List[Dict[str, Any]]
