"""
Zingér UP Exact Paper-Replica Arabic PDF Generator for Project # hasep.
Faithfully reproduces the layout, fonts, borders, and structure of the physical paper form.
"""

import os
from decimal import Decimal
from typing import Dict, Any, Union
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

from backend.app.schemas.financial_form import FinancialFormData

ARABIC_FONT_PATH = "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"
ARABIC_BOLD_FONT_PATH = "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf"

FONT_NAME = "NotoArabic"
BOLD_FONT_NAME = "NotoArabic-Bold"

try:
    if os.path.exists(ARABIC_FONT_PATH):
        pdfmetrics.registerFont(TTFont(FONT_NAME, ARABIC_FONT_PATH))
    else:
        FONT_NAME = "Helvetica"

    if os.path.exists(ARABIC_BOLD_FONT_PATH):
        pdfmetrics.registerFont(TTFont(BOLD_FONT_NAME, ARABIC_BOLD_FONT_PATH))
    else:
        BOLD_FONT_NAME = FONT_NAME
except Exception:
    FONT_NAME = "Helvetica"
    BOLD_FONT_NAME = "Helvetica-Bold"


def ar(text: Any) -> str:
    """Reshape and reorder Arabic text for RTL printing."""
    if text is None:
        return ""
    s = str(text).strip()
    if not s:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(s)
        return get_display(reshaped)
    except Exception:
        return s


def fmt_amt(val: Any) -> str:
    """Format monetary numbers cleanly (e.g. '200' or '200.00')."""
    if val is None or val == "" or val == "0" or val == 0:
        return ""
    try:
        d = Decimal(str(val))
        if d == Decimal("0.00") or d == Decimal("0"):
            return ""
        # If integer amount, display cleanly
        if d == d.to_integral():
            return f"{int(d)}"
        return f"{d:.2f}"
    except Exception:
        return str(val)


def generate_financial_form_pdf(
    form_input: Union[Dict[str, Any], FinancialFormData],
    output_pdf_path: str
) -> str:
    return _generate_financial_form_pdf_impl(form_input, output_pdf_path)
exec('def _generate_financial_form_pdf_impl(\n    form_input: Union[Dict[str, Any], FinancialFormData],\n    output_pdf_path: str\n) -> str:\n    """\n    Renders an exact 1:1 replica of the Zinger UP physical paper form.\n    """\n    if isinstance(form_input, FinancialFormData):\n        data = form_input.model_dump(mode="json")\n    else:\n        data = form_input\n    os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)\n    doc = SimpleDocTemplate(\n        output_pdf_path,\n        pagesize=A4,\n        rightMargin=25,\n        leftMargin=25,\n        topMargin=25,\n        bottomMargin=20,\n    )\n    hdr_store = ParagraphStyle("HdrStore", fontName=BOLD_FONT_NAME, fontSize=11, leading=14, alignment=2) # Right\n    hdr_logo = ParagraphStyle("HdrLogo", fontName="Helvetica-Bold", fontSize=15, leading=16, alignment=1) # Center\n    hdr_sublogo = ParagraphStyle("HdrSubLogo", fontName="Helvetica-Oblique", fontSize=7, leading=9, alignment=1)\n    hdr_phone = ParagraphStyle("HdrPhone", fontName="Helvetica-Bold", fontSize=9, leading=12, alignment=0) # Left\n    date_style = ParagraphStyle("DateStyle", fontName="Helvetica-Bold", fontSize=9, leading=11, alignment=0)\n    day_style = ParagraphStyle("DayStyle", fontName=BOLD_FONT_NAME, fontSize=9, leading=11, alignment=2)\n    tbl_hdr = ParagraphStyle("TblHdr", fontName=BOLD_FONT_NAME, fontSize=9, leading=11, alignment=1)\n    cell_txt = ParagraphStyle("CellTxt", fontName=FONT_NAME, fontSize=9, leading=11, alignment=1)\n    cell_bold = ParagraphStyle("CellBold", fontName=BOLD_FONT_NAME, fontSize=9, leading=11, alignment=1)\n    lbl_right = ParagraphStyle("LblRight", fontName=BOLD_FONT_NAME, fontSize=8, leading=10, alignment=2)\n    story = []\n    center_logo = [\n        Paragraph("ZingérUP", hdr_logo),\n        Paragraph("Zinger World", hdr_sublogo),\n    ]\n    header_table_data = [\n        [\n            Paragraph("0795235333 - Taj Mall", hdr_phone),\n            center_logo,\n            Paragraph(ar("مطعم زنجر Up"), hdr_store),\n        ]\n    ]\n    t_header = Table(header_table_data, colWidths=[180, 185, 180])\n    t_header.setStyle(TableStyle([\n        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),\n        ("ALIGN", (0, 0), (0, 0), "LEFT"),\n        ("ALIGN", (1, 0), (1, 0), "CENTER"),\n        ("ALIGN", (2, 0), (2, 0), "RIGHT"),\n        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),\n    ]))\n    story.append(t_header)\n    story.append(Spacer(1, 4))\n    raw_date = data.get("form_date", "2026-11-13")\n    parts = raw_date.split("-")\n    if len(parts) == 3:\n        y, m, d = parts[0], parts[1], parts[2]\n        date_display = f"DATE:   {d}  /  {m}  /{y}"\n    else:\n        date_display = f"DATE:   {raw_date}"\n    day_name = data.get("day_of_week", "")\n    day_display = ar(f"DAY:   {day_name}")\n    date_table_data = [\n        [\n            Paragraph(date_display, date_style),\n            Paragraph(day_display, day_style),\n        ]\n    ]\n    t_date = Table(date_table_data, colWidths=[270, 275])\n    t_date.setStyle(TableStyle([\n        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),\n        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),\n    ]))\n    story.append(t_date)\n    story.append(Spacer(1, 4))\n    main_cols = [90, 90, 155, 105, 105]  # Left to right in ReportLab: [خروج, دخول, الموظف, المشتريات, المصاريف]\n    table_rows = [\n        [\n            Paragraph(ar("خروج"), tbl_hdr),\n            Paragraph(ar("دخول"), tbl_hdr),\n            Paragraph(ar("الموظف"), tbl_hdr),\n            Paragraph(ar("المشتريات"), tbl_hdr),\n            Paragraph(ar("المصاريف"), tbl_hdr),\n        ]\n    ]\n    attendance = data.get("attendance", [])\n    purchases = data.get("purchases", [])\n    expenses = data.get("expenses", [])\n    for r in range(10):\n        exp_item = expenses[r] if r < len(expenses) else {}\n        exp_val = fmt_amt(exp_item.get("amount", ""))\n        purch_item = purchases[r] if r < len(purchases) else {}\n        purch_val = fmt_amt(purch_item.get("amount", ""))\n        att_item = attendance[r] if r < len(attendance) else {}\n        emp_name = ar(att_item.get("employee_name", ""))\n        entry_t = ar(att_item.get("entry_time", ""))\n        exit_t = ar(att_item.get("exit_time", ""))\n        table_rows.append([\n            Paragraph(exit_t, cell_txt),\n            Paragraph(entry_t, cell_txt),\n            Paragraph(emp_name, cell_bold),\n            Paragraph(purch_val, cell_bold),\n            Paragraph(exp_val, cell_bold),\n        ])\n    t_main = Table(table_rows, colWidths=main_cols, rowHeights=[20] + [22] * 10)\n    t_main.setStyle(TableStyle([\n        ("GRID", (0, 0), (-1, -1), 0.75, colors.black),\n        ("ALIGN", (0, 0), (-1, -1), "CENTER"),\n        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),\n        ("TOPPADDING", (0, 0), (-1, -1), 1),\n        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),\n    ]))\n    story.append(t_main)\n    summary = data.get("summary", {})\n    tot_exp = fmt_amt(summary.get("total_expenses", ""))\n    tot_purch = fmt_amt(summary.get("total_purchases", ""))\n    tot_both = fmt_amt(summary.get("total_expenses_and_purchases", ""))\n    subtotals_data = [\n        [\n            Paragraph(ar("مجموع المصاريف والمشتريات:"), lbl_right),\n            Paragraph(ar("المجموع الكلي:"), lbl_right),\n            Paragraph(ar("المجموع الكلي:"), lbl_right),\n        ],\n        [\n            Paragraph(tot_both, cell_bold),\n            Paragraph(tot_purch, cell_bold),\n            Paragraph(tot_exp, cell_bold),\n        ],\n    ]\n    t_subtotals = Table(subtotals_data, colWidths=[335, 105, 105], rowHeights=[16, 24])\n    t_subtotals.setStyle(TableStyle([\n        ("GRID", (0, 0), (-1, -1), 0.75, colors.black),\n        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),\n        ("ALIGN", (0, 1), (-1, 1), "CENTER"),\n        ("TOPPADDING", (0, 0), (-1, -1), 1),\n        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),\n    ]))\n    story.append(t_subtotals)\n    sales = data.get("sales", {})\n    visa_val = fmt_amt(sales.get("visa", ""))\n    talabat_val = fmt_amt(sales.get("orders", ""))\n    kareem_val = fmt_amt(sales.get("kareem", ""))\n    ashaayi_val = fmt_amt(sales.get("ashaayi", ""))\n    apps_col_w = 545 / 4  # 136.25\n    apps_data = [\n        [\n            Paragraph(ar("أشيائي:"), lbl_right),\n            Paragraph(ar("كريم:"), lbl_right),\n            Paragraph(ar("طلبات:"), lbl_right),\n            Paragraph(ar("الفيزا:"), lbl_right),\n        ],\n        [\n            Paragraph(ashaayi_val, cell_bold),\n            Paragraph(kareem_val, cell_bold),\n            Paragraph(talabat_val, cell_bold),\n            Paragraph(visa_val, cell_bold),\n        ],\n    ]\n    t_apps = Table(apps_data, colWidths=[apps_col_w] * 4, rowHeights=[16, 24])\n    t_apps.setStyle(TableStyle([\n        ("GRID", (0, 0), (-1, -1), 0.75, colors.black),\n        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),\n        ("ALIGN", (0, 1), (-1, 1), "CENTER"),\n        ("TOPPADDING", (0, 0), (-1, -1), 1),\n        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),\n    ]))\n    story.append(t_apps)\n    prev_bal = fmt_amt(summary.get("previous_balance", ""))\n    curr_bal = fmt_amt(summary.get("handwritten_current_balance") or summary.get("current_balance", ""))\n    inc_val = fmt_amt(summary.get("increase", ""))\n    dec_val = fmt_amt(summary.get("decrease", ""))\n    if dec_val and not dec_val.endswith("-"):\n        dec_val = f"{dec_val} -"\n    bal_data = [\n        [\n            Paragraph(ar("نقص"), lbl_right),\n            Paragraph(ar("زيادة"), lbl_right),\n            Paragraph(ar("الرصيد الحالي:-"), lbl_right),\n            Paragraph(ar("الرصيد السابق:-"), lbl_right),\n        ],\n        [\n            Paragraph(dec_val, cell_bold),\n            Paragraph(inc_val, cell_bold),\n            Paragraph(curr_bal, cell_bold),\n            Paragraph(prev_bal, cell_bold),\n        ],\n    ]\n    t_bal = Table(bal_data, colWidths=[apps_col_w] * 4, rowHeights=[16, 24])\n    t_bal.setStyle(TableStyle([\n        ("GRID", (0, 0), (-1, -1), 0.75, colors.black),\n        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),\n        ("ALIGN", (0, 1), (-1, 1), "CENTER"),\n        ("TOPPADDING", (0, 0), (-1, -1), 1),\n        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),\n    ]))\n    story.append(t_bal)\n    sales_w = 545 / 3  # ~181.67\n    gross_sales_val = fmt_amt(sales.get("sales", ""))\n    returns_val = fmt_amt(sales.get("returns", ""))\n    net_sales_val = fmt_amt(sales.get("net_sale", ""))\n    sales_data = [\n        [\n            Paragraph(ar("صافي البيع:"), lbl_right),\n            Paragraph(ar("مرتجع:"), lbl_right),\n            Paragraph(ar("المبيعات:"), lbl_right),\n        ],\n        [\n            Paragraph(net_sales_val, cell_bold),\n            Paragraph(returns_val, cell_bold),\n            Paragraph(gross_sales_val, cell_bold),\n        ],\n    ]\n    t_sales = Table(sales_data, colWidths=[sales_w] * 3, rowHeights=[16, 26])\n    t_sales.setStyle(TableStyle([\n        ("GRID", (0, 0), (-1, -1), 0.75, colors.black),\n        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),\n        ("ALIGN", (0, 1), (-1, 1), "CENTER"),\n        ("TOPPADDING", (0, 0), (-1, -1), 1),\n        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),\n    ]))\n    story.append(t_sales)\n    total_sale_val = fmt_amt(sales.get("total_sale", ""))\n    total_apps_val = fmt_amt(sales.get("total_applications", ""))\n    visa_total_val = fmt_amt(sales.get("visa", ""))\n    notes_val = ar(data.get("notes", ""))\n    left_stacked_table = Table(\n        [\n            [Paragraph(total_sale_val, cell_bold), Paragraph(ar("المجموع الكلي للبيع: -"), lbl_right)],\n            [Paragraph(total_apps_val, cell_bold), Paragraph(ar("مجموع التطبيقات:-"), lbl_right)],\n            [Paragraph(visa_total_val, cell_bold), Paragraph(ar("visa الفيزا:-"), lbl_right)],\n        ],\n        colWidths=[112.5, 160],\n        rowHeights=[24, 24, 24]\n    )\n    left_stacked_table.setStyle(TableStyle([\n        ("GRID", (0, 0), (-1, -1), 0.75, colors.black),\n        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),\n        ("ALIGN", (0, 0), (0, -1), "CENTER"),\n        ("TOPPADDING", (0, 0), (-1, -1), 2),\n        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),\n    ]))\n    notes_box = Table(\n        [\n            [Paragraph(ar("ملاحظات:"), lbl_right)],\n            [Paragraph(notes_val, cell_txt)],\n        ],\n        colWidths=[272.5],\n        rowHeights=[16, 56]\n    )\n    notes_box.setStyle(TableStyle([\n        ("GRID", (0, 0), (-1, -1), 0.75, colors.black),\n        ("VALIGN", (0, 0), (-1, 0), "TOP"),\n        ("VALIGN", (0, 1), (-1, 1), "TOP"),\n        ("TOPPADDING", (0, 0), (-1, -1), 2),\n        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),\n    ]))\n    bottom_container = Table(\n        [\n            [left_stacked_table, notes_box]\n        ],\n        colWidths=[272.5, 272.5],\n        rowHeights=[72]\n    )\n    bottom_container.setStyle(TableStyle([\n        ("VALIGN", (0, 0), (-1, -1), "TOP"),\n        ("LEFTPADDING", (0, 0), (-1, -1), 0),\n        ("RIGHTPADDING", (0, 0), (-1, -1), 0),\n        ("TOPPADDING", (0, 0), (-1, -1), 0),\n        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),\n    ]))\n    story.append(bottom_container)\n    doc.build(story)\n    return output_pdf_path\n', globals())
