import pytest
from backend.app.ocr.arabic_utils import (
    normalize_arabic_digits,
    convert_western_to_arabic_digits,
    parse_arabic_number,
    is_arabic_text,
    clean_arabic_string,
)


def test_arabic_digit_normalization():
    assert normalize_arabic_digits("١٢٣٤٥") == "12345"
    assert normalize_arabic_digits("فاتورة رقم ٦٧٨٩") == "فاتورة رقم 6789"
    assert convert_western_to_arabic_digits("12345") == "١٢٣٤٥"


def test_parse_arabic_number():
    # Western digits with dot
    f_val, i_val, is_num = parse_arabic_number("125.50")
    assert is_num is True
    assert f_val == 125.50
    assert i_val is None

    # Arabic digits with Arabic decimal separator '٫'
    f_val, i_val, is_num = parse_arabic_number("١٢٥٫٥٠")
    assert is_num is True
    assert f_val == 125.50

    # Integer with Arabic currency
    f_val, i_val, is_num = parse_arabic_number("٥٠٠ ريال")
    assert is_num is True
    assert i_val == 500

    # SAR currency
    f_val, i_val, is_num = parse_arabic_number("1500 ر.س")
    assert is_num is True
    assert i_val == 1500

    # Non-numeric
    f_val, i_val, is_num = parse_arabic_number("اسم العميل")
    assert is_num is False


def test_arabic_text_detection():
    assert is_arabic_text("شركة الأمل للتجارة") is True
    assert is_arabic_text("Invoice No 12345") is False
    assert is_arabic_text("Mixed نص عربي and English") is True


def test_clean_arabic_string():
    raw = "مستند\x00 تجريبي\r\n"
    assert clean_arabic_string(raw) == "مستند تجريبي"
