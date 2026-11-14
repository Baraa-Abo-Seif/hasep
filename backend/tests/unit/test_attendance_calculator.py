"""
Unit tests for Project # hasep attendance calculator with midnight crossing and Arabic time formats.
"""

from decimal import Decimal
from backend.app.services.attendance_calculator import calculate_work_duration, parse_time_str


def test_standard_work_duration():
    duration = calculate_work_duration("08:00", "16:30")
    assert duration == Decimal("8.50")


def test_midnight_crossing_duration():
    # 20:00 (8:00 PM) to 02:00 (2:00 AM next day) = 6 hours
    duration = calculate_work_duration("20:00", "02:00")
    assert duration == Decimal("6.00")


def test_arabic_am_pm_parsing():
    t_am = parse_time_str("08:30 ص")
    assert t_am == (8, 30)

    t_pm = parse_time_str("02:15 م")
    assert t_pm == (14, 15)


def test_identical_times():
    # Same entry and exit time yields 0.00 hours
    duration = calculate_work_duration("09:00", "09:00")
    assert duration == Decimal("0.00")


def test_absent_and_leave_status():
    duration_absent = calculate_work_duration("08:00", "16:00", status="غائب")
    assert duration_absent == Decimal("0.00")

    duration_leave = calculate_work_duration("08:00", "16:00", status="إجازة")
    assert duration_leave == Decimal("0.00")
