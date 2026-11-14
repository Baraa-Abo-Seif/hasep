from typing import List, Dict, Any, Tuple
from backend.app.schemas.structured_data import ExtractedTableData, ExtractedColumnData
from backend.app.schemas.excel import ColumnMappingItem


class ColumnMapper:
    """Intelligent dynamic column mapping for Arabic document tables to Excel."""

    # Common Arabic synonyms for table matching
    SYNONYMS = {
        "price": ["سعر", "السعر", "مبلغ", "المبلغ", "القيمة", "إجمالي", "price", "amount", "total"],
        "quantity": ["كمية", "الكمية", "عدد", "العدد", "qty", "quantity", "count"],
        "name": ["اسم", "الاسم", "اسم العميل", "اسم الطالب", "اسم المنتج", "البيان", "name", "description", "item"],
        "date": ["تاريخ", "التاريخ", "تاريخ الفاتورة", "اليوم", "date"],
        "id": ["رقم", "الرقم", "كود", "الكود", "معرف", "تسلسل", "م", "id", "code", "no"],
    }

    @classmethod
    def auto_map_columns(
        cls,
        extracted_columns: List[ExtractedColumnData],
        excel_headers: List[str],
    ) -> Dict[str, str]:
        """Automatically find best match between extracted columns and existing Excel headers."""
        mapping: Dict[str, str] = {}
        cleaned_excel_headers = {h.strip().lower(): h for h in excel_headers}
        for col in extracted_columns:
            key_clean = col.key.strip().lower()
            label_clean = col.label.strip().lower()
            matched_header = None
            if label_clean in cleaned_excel_headers:
                matched_header = cleaned_excel_headers[label_clean]
            elif key_clean in cleaned_excel_headers:
                matched_header = cleaned_excel_headers[key_clean]
            else:
                for syn_key, syn_list in cls.SYNONYMS.items():
                    if any(s in label_clean or s in key_clean for s in syn_list):
                        for h_clean, orig_h in cleaned_excel_headers.items():
                            if any(s in h_clean for s in syn_list):
                                matched_header = orig_h
                                break
                    if matched_header:
                        break
            if matched_header:
                mapping[col.key] = matched_header
        return mapping

    @classmethod
    def generate_preview(
        cls,
        table: ExtractedTableData,
        excel_headers: List[str],
        column_mapping: Dict[str, str],
        max_preview_rows: int = 5,
    ) -> Tuple[List[ColumnMappingItem], List[str], List[str], List[Dict[str, Any]]]:
        return _ColumnMapper_generate_preview_impl(cls, table, excel_headers, column_mapping, max_preview_rows)

exec('def _ColumnMapper_generate_preview_impl(\n    cls,\n    table: ExtractedTableData,\n    excel_headers: List[str],\n    column_mapping: Dict[str, str],\n    max_preview_rows: int = 5,\n) -> Tuple[List[ColumnMappingItem], List[str], List[str], List[Dict[str, Any]]]:\n    """Validates column mapping and generates sample rows for user confirmation."""\n    mapped_items: List[ColumnMappingItem] = []\n    unmapped: List[str] = []\n    missing_required: List[str] = []\n    col_dict = {col.key: col for col in table.columns}\n    for col in table.columns:\n        if col.key in column_mapping and column_mapping[col.key]:\n            mapped_items.append(\n                ColumnMappingItem(\n                    extracted_key=col.key,\n                    extracted_label=col.label,\n                    excel_column_name=column_mapping[col.key],\n                    data_type=col.data_type,\n                )\n            )\n        else:\n            unmapped.append(col.label)\n            if col.is_required:\n                missing_required.append(col.label)\n    sample_rows: List[Dict[str, Any]] = []\n    for row in table.rows[:max_preview_rows]:\n        preview_row = {}\n        for item in mapped_items:\n            cell = row.values.get(item.extracted_key)\n            preview_row[item.excel_column_name] = cell.value if cell else None\n        sample_rows.append(preview_row)\n    return mapped_items, unmapped, missing_required, sample_rows\n', globals())
