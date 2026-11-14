from typing import Optional, List
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    # Normalized [0..1] or pixel coordinates
    x: float
    y: float
    width: float
    height: float
    polygon: Optional[List[float]] = None  # [x1, y1, x2, y2, x3, y3, x4, y4]


class OCRWord(BaseModel):
    text: str
    confidence: float = 1.0
    bounding_box: Optional[BoundingBox] = None
    is_handwritten: bool = False


class OCRLine(BaseModel):
    text: str
    confidence: float = 1.0
    bounding_box: Optional[BoundingBox] = None
    words: List[OCRWord] = Field(default_factory=list)


class OCRTableCell(BaseModel):
    row_index: int
    column_index: int
    row_span: int = 1
    column_span: int = 1
    content: str
    confidence: Optional[float] = None
    bounding_box: Optional[BoundingBox] = None


class OCRTable(BaseModel):
    row_count: int
    column_count: int
    cells: List[OCRTableCell] = Field(default_factory=list)
    bounding_box: Optional[BoundingBox] = None


class NormalizedOCRResult(BaseModel):
    document_id: str
    page_number: int = 1
    provider: str
    language: str = "ar"
    full_text: str
    average_confidence: float = 1.0
    lines: List[OCRLine] = Field(default_factory=list)
    words: List[OCRWord] = Field(default_factory=list)
    tables: List[OCRTable] = Field(default_factory=list)
    raw_response: Optional[dict] = None
