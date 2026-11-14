import re
from typing import List, Dict, Any, Set
from backend.app.schemas.structured_data import (
    DocumentExtractionResult,
    ExtractedTableData,
    ValidationErrorData,
)
from backend.app.ocr.arabic_utils import parse_arabic_number


class DocumentDataValidator:
    """Independent validation layer for extracted document data (Section 11)."""

    DATE_PATTERNS = [
        re.compile(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$"),  # 2026-05-14 or 2026/05/14
        re.compile(r"^\d{1,2}[-/.]\d{1,2}[-/.]\d{4}$"),  # 14-05-2026 or 14/05/2026
    ]

    @classmethod
    def validate_extraction(cls, extraction: DocumentExtractionResult) -> List[ValidationErrorData]:
        """Run comprehensive validation on extracted tables and cells.
        Returns list of ValidationErrorData.
        """
        errors: List[ValidationErrorData] = []

        if not extraction.tables:
            errors.append(
                ValidationErrorData(
                    validation_type="no_tables_found",
                    severity="warning",
                    message="لم يتم العثور على أي جداول في المستند.",
                )
            )
            return errors

        for table in extraction.tables:
            cls._validate_table(table, errors)

        return errors

    @classmethod
    def _validate_table(cls, table: ExtractedTableData, errors: List[ValidationErrorData]) -> None:
        return _DocumentDataValidator__validate_table_impl(cls, table, errors)

exec('def _DocumentDataValidator__validate_table_impl(cls, table: ExtractedTableData, errors: List[ValidationErrorData]) -> None:\n    if not table.columns:\n        errors.append(\n            ValidationErrorData(\n                table_id=table.table_id,\n                validation_type="empty_columns",\n                severity="error",\n                message=f"الجدول \'{table.title}\' لا يحتوي على أي أعمدة معرفة.",\n            )\n        )\n        return\n    col_dict = {col.key: col for col in table.columns}\n    seen_row_signatures: Dict[str, int] = {}\n    for row in table.rows:\n        row_signature_parts = []\n        for col in table.columns:\n            cell = row.values.get(col.key)\n            val_str = str(cell.value).strip() if cell and cell.value is not None else ""\n            row_signature_parts.append(val_str)\n        row_sig = "||".join(row_signature_parts)\n        if row_sig and any(row_signature_parts):\n            if row_sig in seen_row_signatures:\n                prev_row = seen_row_signatures[row_sig]\n                errors.append(\n                    ValidationErrorData(\n                        table_id=table.table_id,\n                        row_number=row.row_number,\n                        validation_type="duplicate_row_warning",\n                        severity="warning",\n                        message=f"تحذير: الصف رقم {row.row_number} متطابق مع الصف رقم {prev_row}. يرجى مراجعته.",\n                    )\n                )\n            else:\n                seen_row_signatures[row_sig] = row.row_number\n        for col_key, col in col_dict.items():\n            cell = row.values.get(col_key)\n            if not cell or cell.value is None or str(cell.value).strip() == "":\n                if col.is_required:\n                    errors.append(\n                        ValidationErrorData(\n                            table_id=table.table_id,\n                            row_number=row.row_number,\n                            column_key=col_key,\n                            validation_type="missing_required_field",\n                            severity="error",\n                            message=f"الحقل المطلوب \'{col.label}\' فارغ في الصف رقم {row.row_number}.",\n                        )\n                    )\n                continue\n            val = cell.value\n            if col.data_type in ("number", "decimal"):\n                val_str = str(val)\n                f_val, i_val, is_num = parse_arabic_number(val_str)\n                if not is_num:\n                    errors.append(\n                        ValidationErrorData(\n                            table_id=table.table_id,\n                            row_number=row.row_number,\n                            column_key=col_key,\n                            validation_type="type_mismatch_number",\n                            severity="error",\n                            message=f"القيمة \'{val}\' في حقل \'{col.label}\' ليست رقماً صحيحاً أو عشرياً.",\n                        )\n                    )\n            elif col.data_type == "date":\n                val_str = str(val).strip()\n                is_date = any(pat.match(val_str) for pat in cls.DATE_PATTERNS)\n                if not is_date:\n                    errors.append(\n                        ValidationErrorData(\n                            table_id=table.table_id,\n                            row_number=row.row_number,\n                            column_key=col_key,\n                            validation_type="invalid_date_format",\n                            severity="warning",\n                            message=f"تنسيق التاريخ \'{val}\' في حقل \'{col.label}\' غير قياسي.",\n                        )\n                    )\n            if cell.needs_review:\n                errors.append(\n                    ValidationErrorData(\n                        table_id=table.table_id,\n                        row_number=row.row_number,\n                        column_key=col_key,\n                        validation_type="needs_review",\n                        severity="info",\n                        message=f"الخلية تتطلب مراجعة: {cell.uncertainty_reason or \'قيمة غير مؤكدة\'}",\n                    )\n                )\n', globals())
