"""
Unit tests for Project # hasep deterministic financial calculations and mismatch detection.
"""

from decimal import Decimal
from backend.app.schemas.financial_form import (
    FinancialFormData,
    PurchaseItem,
    ExpenseItem,
    SalesData,
    SummaryData,
)
from backend.app.services.financial_calculator import recalculate_financial_form


def test_eight_financial_equations():
    form = FinancialFormData(
        form_date="2026-11-13",
        day_of_week="الجمعة",
        purchases=[
            PurchaseItem(item="بند 1", amount=Decimal("25.50")),
            PurchaseItem(item="بند 2", amount=Decimal("74.50")),
        ],
        expenses=[
            ExpenseItem(item="مصروف 1", amount=Decimal("15.25")),
            ExpenseItem(item="مصروف 2", amount=Decimal("4.75")),
        ],
        sales=SalesData(
            sales=Decimal("500.00"),
            returns=Decimal("20.00"),
            orders=Decimal("40.00"),
            kareem=Decimal("30.00"),
            ashaayi=Decimal("20.00"),
            visa=Decimal("110.00"),
        ),
        summary=SummaryData(
            previous_balance=Decimal("200.00"),
            increase=Decimal("150.00"),
            decrease=Decimal("50.00"),
        ),
    )

    recalculated = recalculate_financial_form(form)

    # EQ 1: total_expenses = sum(expenses)
    assert recalculated.summary.total_expenses == Decimal("20.00")

    # EQ 2: total_purchases = sum(purchases)
    assert recalculated.summary.total_purchases == Decimal("100.00")

    # EQ 3: total_expenses_and_purchases = total_expenses + total_purchases
    assert recalculated.summary.total_expenses_and_purchases == Decimal("120.00")

    # EQ 4: net_sale = sales - returns (500 - 20 = 480)
    assert recalculated.sales.net_sale == Decimal("480.00")

    # EQ 5: total_applications = orders + kareem + ashaayi (40 + 30 + 20 = 90)
    assert recalculated.sales.total_applications == Decimal("90.00")

    # EQ 6: total_sale = total_applications + visa + net_sale (90 + 110 + 480 = 680)
    assert recalculated.sales.total_sale == Decimal("680.00")

    # EQ 7: visa = 110.00
    assert recalculated.sales.visa == Decimal("110.00")

    # EQ 8: current_balance = previous_balance + increase - decrease (200 + 150 - 50 = 300)
    assert recalculated.summary.current_balance == Decimal("300.00")

    # No mismatches
    assert recalculated.is_mathematically_valid is True
    assert len(recalculated.calculation_mismatches) == 0


def test_handwritten_balance_mismatch_detection():
    form = FinancialFormData(
        form_date="2026-11-13",
        day_of_week="الجمعة",
        sales=SalesData(sales=Decimal("100.00")),
        summary=SummaryData(
            previous_balance=Decimal("100.00"),
            increase=Decimal("50.00"),
            decrease=Decimal("20.00"),
            # Calculated is 130.00, but handwritten is 125.00 (difference of 5.00)
            handwritten_current_balance=Decimal("125.00"),
        ),
    )

    recalculated = recalculate_financial_form(form)

    assert recalculated.summary.current_balance == Decimal("130.00")
    assert recalculated.is_mathematically_valid is False
    assert len(recalculated.calculation_mismatches) == 1

    mismatch = recalculated.calculation_mismatches[0]
    assert mismatch.equation_id == "EQ8_CURRENT_BALANCE"
    assert mismatch.extracted_value == Decimal("125.00")
    assert mismatch.calculated_value == Decimal("130.00")
    assert mismatch.difference == Decimal("-5.00")
