from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ExcelWorkbookInfo(BaseModel):
    id: str
    name: str
    web_url: Optional[str] = None
    last_modified_date_time: Optional[str] = None


class ExcelWorksheetInfo(BaseModel):
    id: str
    name: str
    position: Optional[int] = None
    visibility: Optional[str] = "Visible"


class ExcelTableInfo(BaseModel):
    id: str
    name: str
    show_headers: bool = True
    columns: List[str] = Field(default_factory=list)


class ColumnMappingItem(BaseModel):
    extracted_key: str
    extracted_label: str
    excel_column_name: str
    data_type: str = "string"


class ExportPreviewRequest(BaseModel):
    document_id: str
    table_id: str
    workbook_id: str
    worksheet_id: Optional[str] = None
    excel_table_id: Optional[str] = None
    column_mapping: Dict[str, str]  # extracted_key -> excel_column_name


class ExportPreviewResponse(BaseModel):
    document_id: str
    table_id: str
    workbook_name: str
    worksheet_name: Optional[str] = None
    target_table_name: Optional[str] = None
    mapped_columns: List[ColumnMappingItem]
    unmapped_columns: List[str]
    missing_required_columns: List[str]
    total_rows_to_export: int
    sample_preview_rows: List[Dict[str, Any]]
    account_type: str
    export_mode: str  # 'graph_table' or 'openpyxl_personal_onedrive'


class ExportConfirmRequest(BaseModel):
    document_id: str
    table_id: str
    workbook_id: str
    workbook_name: str
    worksheet_id: Optional[str] = None
    worksheet_name: Optional[str] = None
    excel_table_id: Optional[str] = None
    excel_table_name: Optional[str] = None
    column_mapping: Dict[str, str]
    idempotency_key: str


class ExportResultResponse(BaseModel):
    export_id: str
    status: str  # 'success', 'partial', 'failed'
    rows_exported: int
    export_mode: str
    target_workbook: str
    target_worksheet: Optional[str] = None
    target_table: Optional[str] = None
    verified: bool
    verification_details: Dict[str, Any] = Field(default_factory=dict)
    message: str
