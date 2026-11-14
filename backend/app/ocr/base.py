from abc import ABC, abstractmethod
from backend.app.schemas.ocr import NormalizedOCRResult


class BaseOCRProvider(ABC):
    """Abstract interface for document OCR and layout analysis engines."""

    @abstractmethod
    async def process_document(
        self,
        image_path: str,
        document_id: str,
        page_number: int = 1,
        use_layout_model: bool = True,
    ) -> NormalizedOCRResult:
        """Process image file and return normalized OCR structure containing full text,
        geometry coordinates (bounding boxes), lines, words, confidence scores, and tables.
        """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if credentials and endpoint are fully configured for live extraction."""
        pass
