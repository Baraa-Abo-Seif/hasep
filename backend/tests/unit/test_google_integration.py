"""
Unit tests for Google OAuth 2.0 and Google Sheets Integration in Project # hasep.
Tests security, CSRF protection, token encryption, formula generation, and idempotency.
"""

import time
import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal

from backend.app.integrations.google.auth import GoogleAuthService
from backend.app.integrations.google.sheets import GoogleSheetsService
from backend.app.core.security import encrypt_token, decrypt_token
from backend.app.schemas.financial_form import (
    FinancialFormData,
    PurchaseItem,
    ExpenseItem,
    EmployeeAttendanceItem,
    SalesData,
    SummaryData,
)


def test_google_token_encryption_roundtrip():
    """Verify that OAuth access & refresh tokens are encrypted using Fernet and safely decrypted."""
    raw_token = "ya29.a0AfH6SMD_EXAMPLE_OAUTH_TOKEN_TEST_1234567890"
    encrypted = encrypt_token(raw_token)
    assert encrypted != raw_token
    assert len(encrypted) > len(raw_token)
    decrypted = decrypt_token(encrypted)
    assert decrypted == raw_token


def test_google_oauth_state_generation_and_tamper_detection():
    """Verify cryptographically signed state generation, expiration, and CSRF tamper detection."""
    service = GoogleAuthService()
    user_id = "test-user-uuid-1234"

    # 1. Valid state
    state = service.generate_secure_state(user_id)
    assert ":" in state
    verified_id = service.verify_state(state)
    assert verified_id == user_id

    # 2. Tampered signature
    tampered = state[:-4] + "abcd"
    assert service.verify_state(tampered) is None

    # 3. Tampered user_id
    parts = state.split(":")
    tampered_user = f"attacker-id:{parts[1]}:{parts[2]}:{parts[3]}"
    assert service.verify_state(tampered_user) is None

    # 4. Expired state
    with patch("time.time", return_value=time.time() + 1000):
        assert service.verify_state(state, max_age_seconds=900) is None


def test_google_sheets_daily_block_formulas_and_layout():
    """
    Verify that Google Sheets daily block contains exact paper form structure
    and native formulas matching # hasep deterministic rules.
    """
    mock_creds = MagicMock()
    with patch("backend.app.integrations.google.sheets.build") as mock_build:
        mock_sheets_api = MagicMock()
        mock_build.return_value = mock_sheets_api

        # Mock spreadsheet metadata
        mock_sheets_api.spreadsheets().get().execute.return_value = {
            "sheets": [{"properties": {"title": "2026-11", "sheetId": 12345}}]
        }
        # Mock values check (empty column A)
        mock_sheets_api.spreadsheets().values().get().execute.return_value = {
            "values": []
        }
        # Mock update
        mock_sheets_api.spreadsheets().values().update().execute.return_value = {"updatedCells": 184}
        mock_sheets_api.spreadsheets().batchUpdate().execute.return_value = {}

        service = GoogleSheetsService(mock_creds)

        form = FinancialFormData(
            form_date="2026-11-14",
            day_of_week="السبت",
            purchases=[
                PurchaseItem(item="دجاج طازج", amount=Decimal("150.00")),
                PurchaseItem(item="زيت قلي", amount=Decimal("50.00")),
            ],
            expenses=[
                ExpenseItem(item="فواتير كهرباء", amount=Decimal("75.00")),
                ExpenseItem(item="أكياس تغليف", amount=Decimal("25.00")),
            ],
            attendance=[
                EmployeeAttendanceItem(employee_name="محمد", entry_time="09:00", exit_time="17:00", duration_hours=Decimal("8.00")),
            ],
            sales=SalesData(
                sales=Decimal("500.00"),
                returns=Decimal("20.00"),
                net_sale=Decimal("480.00"),
                total_sale=Decimal("680.00"),
            ),
            summary=SummaryData(
                previous_balance=Decimal("200.00"),
                current_balance=Decimal("220.00"),
                excess=Decimal("30.00"),
                deficit=Decimal("10.00"),
            ),
        )

        record_id = "test-rec-98765432"
        res = service.append_daily_block("mock_sheet_id", form, record_id)

        assert res["status"] == "synced"
        assert res["sheet_name"] == "2026-11"

        # Verify update call values payload
        update_call = mock_sheets_api.spreadsheets().values().update.call_args
        assert update_call is not None
        payload_values = update_call[1]["body"]["values"]

        # Check header
        assert "مطعم زنجر Up" in payload_values[0][0]
        assert f"[AYA_RECORD_ID:{record_id}]" in payload_values[0][7]

        # Check subtotal formulas in row 14 (index 13)
        subtotals_row = payload_values[13]
        assert subtotals_row[0] == "المجموع الكلي للمصاريف"
        assert "=SUM(B" in subtotals_row[1]  # Expense formula
        assert "=SUM(D" in subtotals_row[3]  # Purchase formula
        assert "=B" in subtotals_row[5] and "+D" in subtotals_row[5]  # Total exp+pur

        # Check cash balance formula in row 18 (index 17)
        cash_row = payload_values[17]
        assert "=B" in cash_row[3] and "+F" in cash_row[3] and "-H" in cash_row[3]

        # Check net sales formula in row 20 (index 19)
        sales_row = payload_values[19]
        assert "=B" in sales_row[5] and "-D" in sales_row[5]


def test_google_sheets_idempotency_prevents_duplicate():
    """Verify that attempting to append an already synced record returns 'already_synced'."""
    mock_creds = MagicMock()
    with patch("backend.app.integrations.google.sheets.build") as mock_build:
        mock_sheets_api = MagicMock()
        mock_build.return_value = mock_sheets_api

        # Mock metadata
        mock_sheets_api.spreadsheets().get().execute.return_value = {
            "sheets": [{"properties": {"title": "2026-11", "sheetId": 12345}}]
        }
        # Mock values check returning existing record marker
        record_id = "already-synced-uuid"
        mock_sheets_api.spreadsheets().values().get().execute.return_value = {
            "values": [["header"], [f"Some text [AYA_RECORD_ID:{record_id}]"]]
        }

        service = GoogleSheetsService(mock_creds)
        form = FinancialFormData(form_date="2026-11-14", day_of_week="السبت")

        res = service.append_daily_block("mock_sheet_id", form, record_id)

        assert res["status"] == "already_synced"
        # values.update MUST NOT be called!
        assert mock_sheets_api.spreadsheets().values().update.call_count == 0
