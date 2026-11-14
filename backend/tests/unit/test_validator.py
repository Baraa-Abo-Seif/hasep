import pytest
from backend.app.schemas.structured_data import (
    DocumentExtractionResult,
    ExtractedTableData,
    ExtractedColumnData,
    ExtractedRowData,
    ExtractedCellData,
)
from backend.app.ai.validator import DocumentDataValidator


def test_validator_detects_missing_required_fields():
    columns = [
        ExtractedColumnData(key="product", label="اسم الصنف", data_type="string", is_required=True),
        ExtractedColumnData(key="price", label="السعر", data_type="decimal", is_required=True),
    ]
    rows = [
        ExtractedRowData(
            row_number=1,
            values={
                "product": ExtractedCellData(value="قلم رصاص"),
                "price": ExtractedCellData(value=None),  # Missing required field!
            },
        )
    ]
    table = ExtractedTableData(table_id="tbl_1", title="جدول الأسعار", columns=columns, rows=rows)
    extraction = DocumentExtractionResult(document_id="doc_1", tables=[table])

    errors = DocumentDataValidator.validate_extraction(extraction)
    assert any(e.validation_type == "missing_required_field" for e in errors)


def test_validator_detects_duplicate_row_warnings():
    columns = [
        ExtractedColumnData(key="name", label="الاسم", data_type="string"),
        ExtractedColumnData(key="score", label="الدرجة", data_type="number"),
    ]
    rows = [
        ExtractedRowData(
            row_number=1,
            values={
                "name": ExtractedCellData(value="أحمد محمد"),
                "score": ExtractedCellData(value=95),
            },
        ),
        ExtractedRowData(
            row_number=2,
            values={
                "name": ExtractedCellData(value="أحمد محمد"),
                "score": ExtractedCellData(value=95),  # Exact duplicate
            },
        ),
    ]
    table = ExtractedTableData(table_id="tbl_1", title="الدرجات", columns=columns, rows=rows)
    extraction = DocumentExtractionResult(document_id="doc_1", tables=[table])

    errors = DocumentDataValidator.validate_extraction(extraction)
    assert any(e.validation_type == "duplicate_row_warning" for e in errors)


def test_validator_invalid_number():
    columns = [
        ExtractedColumnData(key="amount", label="المبلغ", data_type="decimal"),
    ]
    rows = [
        ExtractedRowData(
            row_number=1,
            values={
                "amount": ExtractedCellData(value="غير متوفر"),  # Text instead of number
            },
        )
    ]
    table = ExtractedTableData(table_id="tbl_1", title="الحسابات", columns=columns, rows=rows)
    extraction = DocumentExtractionResult(document_id="doc_1", tables=[table])

    errors = DocumentDataValidator.validate_extraction(extraction)
    assert any(e.validation_type == "type_mismatch_number" for e in errors)
