import datetime
from zoneinfo import ZoneInfo
from typing import Tuple

AMMAN_TZ = ZoneInfo("Asia/Amman")

ARABIC_WEEKDAYS = {
    0: "الإثنين",
    1: "الثلاثاء",
    2: "الأربعاء",
    3: "الخميس",
    4: "الجمعة",
    5: "السبت",
    6: "الأحد",
}


def get_current_amman_date() -> datetime.date:
    """Get today's calendar date in Asia/Amman timezone."""
    return datetime.datetime.now(AMMAN_TZ).date()


def get_arabic_weekday(dt: datetime.date) -> str:
    """Derive Arabic weekday name for a date."""
    return ARABIC_WEEKDAYS[dt.weekday()]


def parse_and_validate_form_date(date_str: str) -> Tuple[datetime.date, str]:
    """Parse YYYY-MM-DD or DD/MM/YYYY date and return (date_obj, arabic_weekday)."""
    clean_date = date_str.strip().replace("/", "-")
    dt = None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            dt = datetime.datetime.strptime(clean_date, fmt).date()
            break
        except ValueError:
            continue
    if not dt:
        raise ValueError(f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD.")
    return dt, get_arabic_weekday(dt)
