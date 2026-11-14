import os
import base64
import json
import logging
from typing import Optional
from openai import AsyncOpenAI

from backend.app.core.config import settings
from backend.app.ai.base import BaseAIUnderstandingProvider
from backend.app.ai.prompts import ARABIC_UNDERSTANDING_SYSTEM_PROMPT, format_user_prompt
from backend.app.ai.validator import DocumentDataValidator
from backend.app.schemas.structured_data import DocumentExtractionResult
from backend.app.schemas.ocr import NormalizedOCRResult

logger = logging.getLogger(__name__)


class OpenAIUnderstandingProvider(BaseAIUnderstandingProvider):
    """OpenAI Vision Document Understanding provider using Structured Outputs."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL_NAME
        self._client: Optional[AsyncOpenAI] = None

        if self.is_configured():
            self._client = AsyncOpenAI(api_key=self.api_key)

    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("<your-"))

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 data URI."""
        ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        mime = f"image/{ext}" if ext in ("jpeg", "jpg", "png", "webp") else "image/jpeg"
        if ext == "jpg":
            mime = "image/jpeg"
            
        with open(image_path, "rb") as img_file:
            b64_data = base64.b64encode(img_file.read()).decode("utf-8")
        return f"data:{mime};base64,{b64_data}"

    def _build_messages(
        self, image_data_uri: str, user_content_text: str, system_prompt: str = ""
    ) -> list:
        return [
            {"role": "system", "content": system_prompt or ARABIC_UNDERSTANDING_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_content_text},
                    {"type": "image_url", "image_url": {"url": image_data_uri, "detail": "high"}},
                ],
            },
        ]

    async def _parse_structured_completion(
        self, messages: list
    ) -> DocumentExtractionResult:
        completion = await self._client.beta.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=DocumentExtractionResult,
            temperature=settings.OPENAI_TEMPERATURE,
        )
        return completion.choices[0].message.parsed

    async def _parse_json_fallback(
        self, user_content_text: str, image_data_uri: str
    ) -> DocumentExtractionResult:
        system = ARABIC_UNDERSTANDING_SYSTEM_PROMPT + (
            "\n\nيجب أن يكون الرد عبارة عن كائن JSON صالح يتبع بدقة بنية DocumentExtractionResult."
        )
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(image_data_uri, user_content_text, system),
            response_format={"type": "json_object"},
            temperature=settings.OPENAI_TEMPERATURE,
        )
        return DocumentExtractionResult.model_validate(
            json.loads(response.choices[0].message.content)
        )

    async def extract_structured_data(
        self,
        image_path: str,
        document_id: str,
        ocr_result: Optional[NormalizedOCRResult] = None,
        user_instructions: str = "",
    ) -> DocumentExtractionResult:
        if not self.is_configured():
            raise RuntimeError(
                "OpenAI API Key is not configured. Please set OPENAI_API_KEY in your .env file."
            )
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at path: {image_path}")
        image_data_uri = self._encode_image(image_path)
        ocr_text = ocr_result.full_text if ocr_result else ""
        user_content_text = format_user_prompt(ocr_text, user_instructions)
        logger.info(f"Invoking OpenAI model {self.model} for document {document_id} structured extraction...")
        messages = self._build_messages(image_data_uri, user_content_text)
        try:
            parsed_result = await self._parse_structured_completion(messages)
        except Exception as e:
            logger.warning(f"Structured parse failed or unsupported, trying fallback with json_object mode: {e}")
            parsed_result = await self._parse_json_fallback(
                user_content_text, image_data_uri
            )
        parsed_result.document_id = document_id
        validation_errors = DocumentDataValidator.validate_extraction(parsed_result)
        parsed_result.validation_errors.extend(validation_errors)
        return parsed_result
