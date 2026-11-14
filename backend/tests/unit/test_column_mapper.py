import pytest
from backend.app.schemas.structured_data import ExtractedColumnData, ExtractedTableData, ExtractedRowData, ExtractedCellData
from backend.app.excel.mapper import ColumnMapper


def test_column_auto_mapping_synonyms():
    extracted_cols = [
        ExtractedColumnData(key="item_desc", label="البيان", data_type="string"),
        ExtractedColumnData(key="item_price", label="المبلغ", data_type="decimal"),
        ExtractedColumnData(key="item_count", label="العدد", data_type="number"),
    ]

    excel_headers = ["اسم الصنف", "السعر", "الكمية", "تاريخ الإضافة"]

    mapping = ColumnMapper.auto_map_columns(extracted_cols, excel_headers)

    # "البيان" should match "اسم الصنف", "المبلغ" should match "السعر", "العدد" should match "الكمية"
    assert mapping.get("item_price") == "السعر"
    assert mapping.get("item_count") == "الكمية"


def test_generate_preview_and_unmapped_columns():
    extracted_cols = [
        ExtractedColumnData(key="col_1", label="الاسم", data_type="string", is_required=True),
        ExtractedColumnData(key="col_2", label="الملاحظات", data_type="string", is_required=False),
    ]
    rows = [
        ExtractedRowData(row_number=1, values={"col_1": ExtractedCellData(value="علي حسام"), "col_2": ExtractedCellData(value="مدفوع")})
    ]
    table = ExtractedTableData(table_id="tbl_1", columns=extracted_cols, rows=rows)

    mapping = {"col_1": "اسم العميل"}  # col_2 unmapped

    mapped, unmapped, missing_req, sample_rows = ColumnMapper.generate_preview(
        table=table,
        excel_headers=["اسم العميل"],
        column_mapping=mapping,
    )

    assert len(mapped) == 1
    assert "الملاحظات" in unmapped
    assert len(missing_req) == 0
    assert sample_rows[0]["اسم العميل"] == "علي حسام"
