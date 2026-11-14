from abc import ABC, abstractmethod
from typing import Optional
from backend.app.schemas.structured_data import DocumentExtractionResult
from backend.app.schemas.ocr import NormalizedOCRResult


class BaseAIUnderstandingProvider(ABC):
    """Abstract interface for AI Document Understanding and table extraction engines."""

    @abstractmethod
    async def extract_structured_data(
        self,
        image_path: str,
        document_id: str,
        ocr_result: Optional[NormalizedOCRResult] = None,
        user_instructions: str = "",
    ) -> DocumentExtractionResult:
        """Analyze document image and OCR text to produce validated structured extraction."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if API keys are configured."""
        pass
