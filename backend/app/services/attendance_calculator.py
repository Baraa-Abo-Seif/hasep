"""
Attendance Calculator for Project # hasep.
Handles work duration calculations with midnight crossing and Arabic/English time formats.
"""

import re
from decimal import Decimal
from typing import Optional, Tuple


def parse_time_str(time_str: Optional[str]) -> Optional[Tuple[int, int]]:
    """
    Parses 24-hour and 12-hour time strings into (hour_24, minute).
    Unmarked plain hours follow the local convention: 10/11 are morning,
    while 1-9 are evening.
    Supports: "14:30", "02:30 م", "8:00 ص", "8:00PM", "20:00", etc.
    """
    if not time_str or not time_str.strip():
        return None

    cleaned = time_str.strip().lower()
    parts = _extract_time_parts(cleaned)
    if parts is None:
        return None
    hour, minute, has_explicit_time = parts
    is_pm = any(marker in cleaned for marker in ["م", "مساء", "pm"])
    is_am = not is_pm and any(marker in cleaned for marker in ["ص", "صباح", "am"])
    if not is_pm and not is_am and not has_explicit_time and hour <= 11:
        is_am, is_pm = hour in (10, 11), hour not in (10, 11)
    hour, minute = _apply_time_marker(hour, minute, is_am, is_pm)
    return (hour, minute) if 0 <= hour <= 23 else None


def _extract_time_parts(cleaned: str) -> Optional[Tuple[int, int, bool]]:
    match = re.search(r"(\d{1,2})[:\.](\d{1,2})", cleaned)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        return hour, 0 if not 0 <= minute <= 59 else minute, True
    single_match = re.search(r"\b(\d{1,2})\b", cleaned)
    return (int(single_match.group(1)), 0, False) if single_match else None


def _apply_time_marker(hour: int, minute: int, is_am: bool, is_pm: bool) -> Tuple[int, int]:
    if is_pm and hour < 12:
        hour += 12
    elif is_am and hour == 12:
        hour = 0
    return hour, minute


def calculate_work_duration(
    entry_time: Optional[str],
    exit_time: Optional[str],
    status: str = "حاضر"
) -> Decimal:
    """
    Calculates duration in hours (Decimal, 2 decimal places).
    Handles midnight crossing: e.g. 20:00 to 02:00 -> 6.00 hours.
    Returns 0.00 for absent/leave status or identical/invalid times.
    """
    if status in ["غائب", "إجازة"]:
        return Decimal("0.00")
    t_in = parse_time_str(entry_time)
    t_out = parse_time_str(exit_time)
    if not t_in or not t_out:
        return Decimal("0.00")
    in_minutes = t_in[0] * 60 + t_in[1]
    out_minutes = t_out[0] * 60 + t_out[1]
    if in_minutes == out_minutes:
        return Decimal("0.00")
    if out_minutes < in_minutes:
        duration_minutes = (24 * 60 - in_minutes) + out_minutes
    else:
        duration_minutes = out_minutes - in_minutes
    hours = Decimal(duration_minutes) / Decimal(60)
    return hours.quantize(Decimal("0.01"))
