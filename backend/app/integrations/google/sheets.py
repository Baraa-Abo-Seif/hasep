"""
Google Sheets Integration Service for Project # hasep.
Handles spreadsheet creation and daily sheet management (YYYY-MM-DD),
and inserting structured daily financial blocks with native Google Sheets formulas.
Enforces strict idempotency and preserves exact paper form layout.
"""

import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from backend.app.schemas.financial_form import FinancialFormData
from backend.app.core.config import settings

logger = logging.getLogger("arabic_excel_platform.google_sheets")


class GoogleSheetsService:
    def __init__(self, credentials: Credentials):
        self.credentials = credentials
        self.service = build("sheets", "v4", credentials=credentials, cache_discovery=False)

    def get_or_create_spreadsheet(self, title: str = "# hasep Financial Records") -> str:
        """
        Creates a new Google Spreadsheet if no ID is configured,
        or verifies accessibility of an existing configured spreadsheet.
        """
        if settings.GOOGLE_SPREADSHEET_ID:
            try:
                sheet_metadata = self.service.spreadsheets().get(
                    spreadsheetId=settings.GOOGLE_SPREADSHEET_ID
                ).execute()
                logger.info(f"Verified existing Google Spreadsheet: {sheet_metadata.get('properties', {}).get('title')}")
                return settings.GOOGLE_SPREADSHEET_ID
            except Exception as e:
                logger.warning(f"Configured GOOGLE_SPREADSHEET_ID could not be accessed ({e}). Creating new sheet...")

        # Create new spreadsheet
        spreadsheet_body = {
            "properties": {
                "title": title,
                "timeZone": "Asia/Amman",
            }
        }
        res = self.service.spreadsheets().create(body=spreadsheet_body, fields="spreadsheetId").execute()
        spreadsheet_id = res.get("spreadsheetId")
        logger.info(f"Created new Google Spreadsheet with ID: {spreadsheet_id}")
        return spreadsheet_id

    def ensure_daily_sheet(self, spreadsheet_id: str, day_name: str) -> int:
        """
        Ensure a sheet named YYYY-MM-DD exists and clear its previous values.
        Returns the sheetId (integer).
        """
        meta = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = meta.get("sheets", [])

        # Check if already exists
        for s in sheets:
            props = s.get("properties", {})
            if props.get("title") == day_name:
                self.service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{day_name}'!A:Z",
                    body={},
                ).execute()
                return props.get("sheetId")

        # If default "Sheet1" or "ورقة 1" is empty and is the only sheet, rename it
        if len(sheets) == 1:
            first_sheet = sheets[0]["properties"]
            if first_sheet.get("title") in ["Sheet1", "ورقة 1", "Sheet 1"]:
                req = {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": first_sheet.get("sheetId"),
                            "title": day_name,
                            "rightToLeft": True,
                            "gridProperties": {"rowCount": 1000, "columnCount": 12},
                        },
                        "fields": "title,rightToLeft,gridProperties",
                    }
                }
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id, body={"requests": [req]}
                ).execute()
                return first_sheet.get("sheetId")

        # Otherwise add a new sheet with RTL enabled
        add_req = {
            "addSheet": {
                "properties": {
                    "title": day_name,
                    "rightToLeft": True,
                    "gridProperties": {"rowCount": 1000, "columnCount": 12},
                }
            }
        }
        res = self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body={"requests": [add_req]}
        ).execute()
        new_sheet_id = res["replies"][0]["addSheet"]["properties"]["sheetId"]
        return new_sheet_id

    def check_record_already_exists(
        self, spreadsheet_id: str, sheet_name: str, record_id: str
    ) -> Optional[int]:
        """
        Scan Column A of the monthly sheet to find whether this record ID is already synced.
        Returns the 1-based start row if found, or None if not present.
        """
        try:
            res = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!A1:H500",
            ).execute()
            rows = res.get("values", [])
            marker = f"[AYA_RECORD_ID:{record_id}]"
            for idx, r in enumerate(rows):
                if any(marker in str(cell) for cell in r):
                    return idx + 1
            return None
        except Exception as e:
            logger.warning(f"Error checking existing record in sheet: {e}")
            return None

    def append_daily_block(
        self,
        spreadsheet_id: str,
        form: FinancialFormData,
        record_id: str,
    ) -> Dict[str, Any]:
        """
        Appends or updates a complete daily financial form block matching the paper sheet layout.
        Uses native Google Sheets formulas for all mathematical relationships.
        Guarantees strict idempotency.
        """
        day_name = form.form_date  # YYYY-MM-DD
        sheet_id = self.ensure_daily_sheet(spreadsheet_id, day_name)

        # Each daily sheet is a replacement target: never append stale values
        # or old record markers from a previous approval.
        self.service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=f"'{day_name}'!A:Z",
            body={},
        ).execute()
        start_row = 1

        r = start_row
        r_table_header = r + 2            # row 3: table headers
        r_data_start = r + 3              # row 4
        r_data_end = r_data_start + 9     # row 13 (10 rows)
        r_tot_labels = r_data_end + 1     # row 14: total labels
        r_tot_values = r_tot_labels + 1   # row 15: total amounts
        r_apps_header = r_tot_values + 1
        r_apps_values = r_apps_header + 1
        r_cash_header = r_apps_values + 1
        r_cash_values = r_cash_header + 1
        r_sales_header = r_cash_values + 1
        r_sales_values = r_sales_header + 1
        r_summary_header = r_sales_values + 1
        r_summary_values = r_summary_header + 1
        block_end_row = r_summary_values

        # Prepare 10 rows of items
        # Columns: A: مبلغ المصاريف | B: مبلغ المشتريات | C: الموظف
        # D: دخول | E: خروج | F: ساعات العمل
        # Expenses / purchases hold ONLY the amount (numeric) so SUM works.
        table_rows = []
        for i in range(10):
            exp_amount = ""
            if i < len(form.expenses):
                amount = float(form.expenses[i].amount)
                exp_amount = amount if amount > 0 else ""

            pur_amount = ""
            if i < len(form.purchases):
                amount = float(form.purchases[i].amount)
                pur_amount = amount if amount > 0 else ""

            emp_name = form.attendance[i].employee_name if i < len(form.attendance) else ""
            emp_in = (form.attendance[i].entry_time or "") if i < len(form.attendance) else ""
            emp_out = (form.attendance[i].exit_time or "") if i < len(form.attendance) else ""
            emp_hrs = float(form.attendance[i].duration_hours) if i < len(form.attendance) and form.attendance[i].duration_hours > 0 else ""

            table_rows.append([exp_amount, pur_amount, emp_name, emp_in, emp_out, emp_hrs])

        # Totals (native formulas)
        formula_exp_total = f"=SUM(A{r_data_start}:A{r_data_end})"
        formula_pur_total = f"=SUM(B{r_data_start}:B{r_data_end})"

        # Apps & Cards (label on top, amount below): A=Visa, B=Talabat, C=Careem, D=Ashyai
        val_visa = float(form.sales.visa) if form.sales and form.sales.visa else 0.0
        val_talabat = float(form.sales.orders) if form.sales and form.sales.orders else 0.0
        val_careem = float(form.sales.kareem) if form.sales and form.sales.kareem else 0.0
        val_ashyai = float(form.sales.ashaayi) if form.sales and form.sales.ashaayi else 0.0

        # Cash balance: A=Prev, B=Current (formula), C=Excess, D=Deficit
        val_prev_cash = float(form.summary.previous_balance) if form.summary and form.summary.previous_balance else 0.0
        val_excess = float(form.summary.increase) if form.summary and form.summary.increase else 0.0
        val_deficit = float(form.summary.decrease) if form.summary and form.summary.decrease else 0.0
        formula_current_cash = f"=A{r_cash_values}+C{r_cash_values}-D{r_cash_values}"

        # Sales: A=Sales, B=Returns, C=Net (formula)
        val_sales = float(form.sales.sales) if form.sales and form.sales.sales else 0.0
        val_returns = float(form.sales.returns) if form.sales and form.sales.returns else 0.0
        formula_net_sales = f"=A{r_sales_values}-B{r_sales_values}"

        # Summary: A=Apps sum, B=Visa, C=Total sales
        formula_apps_sum = f"=B{r_apps_values}+C{r_apps_values}+D{r_apps_values}"
        formula_visa_ref = f"=A{r_apps_values}"
        formula_total_sales = f"=C{r_sales_values}+A{r_apps_values}+A{r_summary_values}"

        form_notes = getattr(form, "notes", None) or "لا توجد ملاحظات"

        values_payload = [
            # Row 1: Title (merged A:G) + Day in the LAST column (H)
            ["مطعم زنجر Up - ZingérUP (0795235333 - Taj Mall)", "", "", "", "", "", "", f"اليوم: {form.day_of_week}"],
            # Row 2: spacer
            ["", "", "", "", "", "", "", ""],
            # Row 3: Table headers
            ["المصاريف", "المشتريات", "الموظف", "وقت الدخول", "وقت الخروج", "الساعات"],
            # Rows 4-13: 10 items (amounts only)
            *table_rows,
            # Row 14: total labels / Row 15: total amounts
            ["المجموع الكلي للمصاريف", "المجموع الكلي للمشتريات"],
            [formula_exp_total, formula_pur_total],
            # Apps: label above, amount below
            ["الفيزا (Visa)", "طلبات (Talabat)", "كريم (Careem)", "أشيائي"],
            [val_visa, val_talabat, val_careem, val_ashyai],
            # Cash balance
            ["الرصيد السابق", "الرصيد الحالي", "زيادة", "نقصان"],
            [val_prev_cash, formula_current_cash, val_excess, val_deficit],
            # Sales
            ["إجمالي المبيعات", "مرتجعات", "صافي البيع"],
            [val_sales, val_returns, formula_net_sales],
            # Summary
            ["مجموع التطبيقات", "فيزا (Visa)", "المجموع الكلي للبيع", "", "ملاحظات وتوجيهات"],
            [formula_apps_sum, formula_visa_ref, formula_total_sales, "", form_notes],
        ]

        # Diagnostic: proves which layout version is actually running on the server
        logger.info(
            "# hasep layout v2 | row %s (apps header) = %r | row %s (cash header) = %r",
            r_apps_header, values_payload[r_apps_header - 1][0],
            r_cash_header, values_payload[r_cash_header - 1][0],
        )

        # 3. Write Values
        write_range = f"'{day_name}'!A{r}:H{block_end_row}"
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=write_range,
            valueInputOption="USER_ENTERED",
            body={"values": values_payload},
        ).execute()

        # 4. Apply Visual Formatting and Borders via batchUpdate
        def rng(r1, r2, c1, c2):
            """1-based inclusive rows, 0-based [c1, c2) columns."""
            return {"sheetId": sheet_id, "startRowIndex": r1 - 1, "endRowIndex": r2,
                    "startColumnIndex": c1, "endColumnIndex": c2}

        label_rows = [r_tot_labels, r_apps_header, r_cash_header, r_sales_header, r_summary_header]
        value_rows = [r_tot_values, r_apps_values, r_cash_values, r_sales_values, r_summary_values]
        dark = {"red": 0.2, "green": 0.2, "blue": 0.2}
        light = {"red": 0.8, "green": 0.8, "blue": 0.8}

        reqs = [
            # Clear any merges left from a previous layout of this sheet
            {"unmergeCells": {"range": rng(1, 40, 0, 12)}},
            # Merge title A:G (H holds the day)
            {"mergeCells": {"range": rng(r, r, 0, 7), "mergeType": "MERGE_ALL"}},
            # Title styling
            {
                "repeatCell": {
                    "range": rng(r, r, 0, 8),
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.06, "green": 0.38, "blue": 0.28},
                            "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 12},
                            "horizontalAlignment": "CENTER",
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
                }
            },
            # Table header styling
            {
                "repeatCell": {
                    "range": rng(r_table_header, r_table_header, 0, 6),
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.90, "green": 0.93, "blue": 0.95},
                            "textFormat": {"bold": True, "fontSize": 10},
                            "horizontalAlignment": "CENTER",
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
                }
            },
            # Currency format: amounts in expenses/purchases + all value rows below
            {
                "repeatCell": {
                    "range": rng(r_data_start, r_data_end, 0, 2),
                    "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.00 \"JOD\""}}},
                    "fields": "userEnteredFormat.numberFormat",
                }
            },
            {
                "repeatCell": {
                    "range": rng(r_tot_values, r_summary_values, 0, 4),
                    "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.00 \"JOD\""}}},
                    "fields": "userEnteredFormat.numberFormat",
                }
            },
            # Merge notes (label row + value row)
            {"mergeCells": {"range": rng(r_summary_header, r_summary_header, 4, 8), "mergeType": "MERGE_ALL"}},
            {"mergeCells": {"range": rng(r_summary_values, r_summary_values, 4, 8), "mergeType": "MERGE_ALL"}},
        ]

        # Label rows: slate background, bold, centered
        for lr in label_rows:
            reqs.append({
                "repeatCell": {
                    "range": rng(lr, lr, 0, 8),
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.90, "green": 0.93, "blue": 0.95},
                            "textFormat": {"bold": True},
                            "horizontalAlignment": "CENTER",
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
                }
            })
        # Value rows: centered
        for vr in value_rows:
            reqs.append({
                "repeatCell": {
                    "range": rng(vr, vr, 0, 8),
                    "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
                    "fields": "userEnteredFormat.horizontalAlignment",
                }
            })

        reqs += [
            # Totals amounts row (amber)
            {
                "repeatCell": {
                    "range": rng(r_tot_values, r_tot_values, 0, 2),
                    "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.98, "green": 0.95, "blue": 0.88}, "textFormat": {"bold": True}}},
                    "fields": "userEnteredFormat(backgroundColor,textFormat)",
                }
            },
            # Grand total of sales (green)
            {
                "repeatCell": {
                    "range": rng(r_summary_values, r_summary_values, 2, 3),
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.85, "green": 0.95, "blue": 0.88},
                            "textFormat": {"bold": True, "fontSize": 11, "foregroundColor": {"red": 0.05, "green": 0.35, "blue": 0.15}},
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat)",
                }
            },
            # Column widths so labels and the day in column H are readable
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 5},
                    "properties": {"pixelSize": 170},
                    "fields": "pixelSize",
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 7, "endIndex": 8},
                    "properties": {"pixelSize": 140},
                    "fields": "pixelSize",
                }
            },
            # Outer borders for the whole block
            {
                "updateBorders": {
                    "range": rng(r, block_end_row, 0, 8),
                    "top": {"style": "SOLID_MEDIUM", "color": dark},
                    "bottom": {"style": "SOLID_MEDIUM", "color": dark},
                    "left": {"style": "SOLID_MEDIUM", "color": dark},
                    "right": {"style": "SOLID_MEDIUM", "color": dark},
                    "innerHorizontal": {"style": "SOLID", "color": light},
                    "innerVertical": {"style": "SOLID", "color": light},
                }
            },
        ]

        try:
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body={"requests": reqs}
            ).execute()
        except Exception as fe:
            logger.warning(f"Could not apply full visual formatting to Google Sheet: {fe}")

        logger.info(
            f"Successfully wrote daily block for {form.form_date} (Record {record_id[:8]}) to sheet '{day_name}' at row {r}."
        )
        return {
            "status": "synced",
            "sheet_name": day_name,
            "start_row": r,
            "end_row": block_end_row,
            "spreadsheet_id": spreadsheet_id,
            "sheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
        }