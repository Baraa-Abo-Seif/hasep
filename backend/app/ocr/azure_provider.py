import os
import logging
from typing import Optional, List
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, AnalyzeResult

from backend.app.core.config import settings
from backend.app.ocr.base import BaseOCRProvider
from backend.app.schemas.ocr import (
    NormalizedOCRResult,
    OCRLine,
    OCRWord,
    OCRTable,
    OCRTableCell,
    BoundingBox,
)
from backend.app.ocr.arabic_utils import clean_arabic_string, is_arabic_text

logger = logging.getLogger(__name__)


class AzureDocumentIntelligenceProvider(BaseOCRProvider):
    """Adapter for Microsoft Azure AI Document Intelligence (Read & Layout models)."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        key: Optional[str] = None,
        read_model: Optional[str] = None,
        layout_model: Optional[str] = None,
    ):
        self.endpoint = endpoint or settings.AZURE_DOC_INTELLIGENCE_ENDPOINT
        self.key = key or settings.AZURE_DOC_INTELLIGENCE_KEY
        self.read_model = read_model or settings.AZURE_OCR_MODEL_READ
        self.layout_model = layout_model or settings.AZURE_OCR_MODEL_LAYOUT

        self._client: Optional[DocumentIntelligenceClient] = None
        if self.is_configured():
            try:
                self._client = DocumentIntelligenceClient(
                    endpoint=self.endpoint,
                    credential=AzureKeyCredential(self.key),
                )
            except Exception as e:
                logger.error(f"Failed to initialize Azure Document Intelligence Client: {e}")

    def is_configured(self) -> bool:
        return bool(
            self.endpoint
            and self.key
            and not self.endpoint.startswith("https://<your-")
            and not self.key.startswith("<your-")
        )

    def _polygon_to_bbox(self, polygon: Optional[List[float]]) -> Optional[BoundingBox]:
        """Convert Azure 8-point polygon [x1, y1, x2, y2, x3, y3, x4, y4] to BoundingBox."""
        if not polygon or len(polygon) < 8:
            return None
        xs = polygon[0::2]
        ys = polygon[1::2]
        min_x = min(xs)
        min_y = min(ys)
        max_x = max(xs)
        max_y = max(ys)
        return BoundingBox(
            x=min_x,
            y=min_y,
            width=max_x - min_x,
            height=max_y - min_y,
            polygon=polygon,
        )

    async def process_document(
        self,
        image_path: str,
        document_id: str,
        page_number: int = 1,
        use_layout_model: bool = True,
    ) -> NormalizedOCRResult:
        return await _AzureDocumentIntelligenceProvider_process_document_impl(self, image_path, document_id, page_number, use_layout_model)

exec('async def _AzureDocumentIntelligenceProvider_process_document_impl(\n    self,\n    image_path: str,\n    document_id: str,\n    page_number: int = 1,\n    use_layout_model: bool = True,\n) -> NormalizedOCRResult:\n    if not self.is_configured():\n        raise RuntimeError(\n            "Azure Document Intelligence is not configured. Please set "\n            "AZURE_DOC_INTELLIGENCE_ENDPOINT and AZURE_DOC_INTELLIGENCE_KEY in your .env file."\n        )\n    model_id = self.layout_model if use_layout_model else self.read_model\n    logger.info(f"Submitting document {document_id} to Azure Document Intelligence using model {model_id}...")\n    if not os.path.exists(image_path):\n        raise FileNotFoundError(f"Image file not found: {image_path}")\n    with open(image_path, "rb") as f:\n        file_bytes = f.read()\n    poller = self._client.begin_analyze_document(\n        model_id=model_id,\n        analyze_request=file_bytes,\n        content_type="application/octet-stream",\n    )\n    result: AnalyzeResult = poller.result()\n    full_text = clean_arabic_string(result.content or "")\n    lines_list: List[OCRLine] = []\n    words_list: List[OCRWord] = []\n    confidences: List[float] = []\n    if result.pages:\n        for page in result.pages:\n            if page.words:\n                for w in page.words:\n                    conf = float(w.confidence) if hasattr(w, "confidence") and w.confidence is not None else 1.0\n                    confidences.append(conf)\n                    bbox = self._polygon_to_bbox(getattr(w, "polygon", None))\n                    words_list.append(\n                        OCRWord(\n                            text=clean_arabic_string(w.content),\n                            confidence=conf,\n                            bounding_box=bbox,\n                            is_handwritten=False,  # Can also be detected from page styles if present\n                        )\n                    )\n            if page.lines:\n                for line in page.lines:\n                    l_bbox = self._polygon_to_bbox(getattr(line, "polygon", None))\n                    lines_list.append(\n                        OCRLine(\n                            text=clean_arabic_string(line.content),\n                            confidence=1.0,\n                            bounding_box=l_bbox,\n                        )\n                    )\n    tables_list: List[OCRTable] = []\n    if result.tables:\n        for tbl in result.tables:\n            cells_list: List[OCRTableCell] = []\n            for cell in tbl.cells:\n                c_bbox = None\n                if getattr(cell, "bounding_regions", None) and len(cell.bounding_regions) > 0:\n                    c_bbox = self._polygon_to_bbox(getattr(cell.bounding_regions[0], "polygon", None))\n                cells_list.append(\n                    OCRTableCell(\n                        row_index=cell.row_index,\n                        column_index=cell.column_index,\n                        row_span=getattr(cell, "row_span", 1) or 1,\n                        column_span=getattr(cell, "column_span", 1) or 1,\n                        content=clean_arabic_string(cell.content),\n                        confidence=getattr(cell, "confidence", 1.0),\n                        bounding_box=c_bbox,\n                    )\n                )\n            tables_list.append(\n                OCRTable(\n                    row_count=tbl.row_count,\n                    column_count=tbl.column_count,\n                    cells=cells_list,\n                )\n            )\n    avg_conf = float(sum(confidences) / len(confidences)) if confidences else 1.0\n    lang = "ar" if is_arabic_text(full_text) else "en"\n    return NormalizedOCRResult(\n        document_id=document_id,\n        page_number=page_number,\n        provider="azure_doc_intelligence",\n        language=lang,\n        full_text=full_text,\n        average_confidence=round(avg_conf, 4),\n        lines=lines_list,\n        words=words_list,\n        tables=tables_list,\n        raw_response={"content_length": len(full_text), "pages_count": len(result.pages or [])},\n    )\n', globals())
