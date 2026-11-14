"""
Unit tests for Asia/Amman date utilities and Arabic weekday derivation.
"""

import datetime
from backend.app.utils.date_utils import (
    get_arabic_weekday,
    parse_and_validate_form_date,
    get_current_amman_date,
)


def test_arabic_weekdays():
    # 2026-11-13 is Friday
    dt_friday = datetime.date(2026, 11, 13)
    assert get_arabic_weekday(dt_friday) == "الجمعة"

    # 2026-11-14 is Saturday
    dt_sat = datetime.date(2026, 11, 14)
    assert get_arabic_weekday(dt_sat) == "السبت"

    # 2026-11-15 is Sunday
    dt_sun = datetime.date(2026, 11, 15)
    assert get_arabic_weekday(dt_sun) == "الأحد"


def test_parse_and_validate_form_date():
    dt, weekday = parse_and_validate_form_date("2026-11-13")
    assert dt == datetime.date(2026, 11, 13)
    assert weekday == "الجمعة"

    # Slash format
    dt2, weekday2 = parse_and_validate_form_date("13/11/2026")
    assert dt2 == datetime.date(2026, 11, 13)
    assert weekday2 == "الجمعة"


def test_current_amman_date():
    today = get_current_amman_date()
    assert isinstance(today, datetime.date)
