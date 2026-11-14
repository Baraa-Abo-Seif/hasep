from typing import Optional
from backend.app.core.config import settings
from backend.app.ocr.base import BaseOCRProvider
from backend.app.ocr.azure_provider import AzureDocumentIntelligenceProvider


def get_ocr_provider(override_provider: Optional[BaseOCRProvider] = None) -> BaseOCRProvider:
    """Return the active OCR provider (default: Azure Document Intelligence)."""
    if override_provider:
        return override_provider
    return AzureDocumentIntelligenceProvider()
