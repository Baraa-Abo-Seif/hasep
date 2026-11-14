"""
Google Gemini Vision & Document Understanding Provider for Project # hasep.
Exclusively uses the official google-genai SDK to analyze Arabic handwritten financial forms.
"""

import json
import logging
import mimetypes
from decimal import Decimal
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types

from backend.app.core.config import settings
from backend.app.utils.date_utils import (
    parse_and_validate_form_date,
    get_current_amman_date,
    get_arabic_weekday,
)
from backend.app.services.attendance_calculator import calculate_work_duration
from backend.app.services.financial_calculator import recalculate_financial_form
from backend.app.schemas.financial_form import (
    FinancialFormData,
    EmployeeAttendanceItem,
    PurchaseItem,
    ExpenseItem,
    SalesData,
    SummaryData,
    OCRUncertainty,
)

logger = logging.getLogger(__name__)

GEMINI_PROMPT = """
أنت خبير معالجة وفهم المستندات المالية المكتوبة بخط اليد باللغة العربية.
المهمة: استخراج البيانات من صورة نموذج الإغلاق المالي اليومي الخاص بمطعم (Zingér UP / مطعم زنجر Up).

هيكل النموذج الورقي المطبوع:
1. الترويسة:
   - في الأعلى: "مطعم زنجر Up" و "0795235333 - Taj Mall" وشعار "ZingérUP".
   - سطر التاريخ: "DATE: DD / MM / 2026" وسطر اليوم: "DAY: اسم اليوم".
2. جدول الدوام والمصاريف والمشتريات (10 أسطر، من اليمين إلى اليسار):
   - العمود 1 (اليمين): "المصاريف" (قيم المبالغ النثرية).
   - العمود 2: "المشتريات" (قيم مبالغ المشتريات).
   - العمود 3: "الموظف" (اسم الموظف).
   - العمود 4: "دخول" (وقت الحضور مثل 11 م أو 2 PM).
   - العمود 5 (اليسار): "خروج" (وقت الانصراف مثل 9 ص أو 12 AM).
3. سطر مجاميع الجدول:
   - تحت المصاريف: "المجموع الكلي:"
   - تحت المشتريات: "المجموع الكلي:"
   - تحت الموظف والدخول والخروج: "مجموع المصاريف والمشتريات:"
4. سطر التطبيقات والفيزا (4 خانات من اليمين لليسار):
   - "الفيزا:" | "طلبات:" | "كريم:" | "أشيائي:" (أو عشائي)
5. سطر مطابقة الرصيد (4 خانات من اليمين لليسار):
   - "الرصيد السابق:-" | "الرصيد الحالي:-" | "زيادة" | "نقص"
6. سطر المبيعات:
   - "المبيعات:" | "مرتجع:" | "صافي البيع:"
7. القسم السفلي:
   - على اليمين: صندوق "ملاحظات:"
   - على اليسار: 3 أسطر:
     * "المجموع الكلي للبيع: -"
     * "مجموع التطبيقات:-"
     * "visa الفيزا:-"

القواعد:
- تحويل كافة الأرقام المشرقية والمغربية إلى أرقام عشرية معيارية (مثلاً 200 أو 200.00). العملة هي الدينار الأردني (JOD).
- إرجاع مصفوفة من 10 أسطر للمصاريف والمشتريات والدوام تطابق أسطر الجدول تماماً.
- إرجاع JSON صالح حصراً بالشكل التالي:

{
  "form_date": "YYYY-MM-DD",
  "day_of_week": "اسم اليوم بالعربية (السبت، الأحد، ...)",
  "attendance": [
    {"employee_name": "اسم الموظف", "entry_time": "11:00 م", "exit_time": "09:00 ص", "notes": ""}
  ],
  "purchases": [
    {"item": "مشتريات سطر 1", "amount": "200.00", "notes": ""}
  ],
  "expenses": [
    {"item": "مصاريف سطر 1", "amount": "300.00", "notes": ""}
  ],
  "sales": {
    "sales": "المبيعات",
    "returns": "المرتجع",
    "net_sale": "صافي البيع",
    "orders": "طلبات",
    "kareem": "كريم",
    "ashaayi": "أشيائي أو عشائي",
    "visa": "الفيزا",
    "total_applications": "مجموع التطبيقات",
    "total_sale": "المجموع الكلي للبيع"
  },
  "summary": {
    "total_expenses": "المجموع الكلي للمصاريف المسجل",
    "total_purchases": "المجموع الكلي للمشتريات المسجل",
    "total_expenses_and_purchases": "مجموع المصاريف والمشتريات المسجل",
    "previous_balance": "الرصيد السابق",
    "current_balance": "الرصيد الحالي",
    "handwritten_current_balance": "الرصيد الحالي المسجل يدوياً",
    "increase": "زيادة",
    "decrease": "نقص"
  },
  "notes": "الملاحظات المدونة أسفل النموذج إن وجدت",
  "uncertainties": []
}
"""


class GeminiFinancialFormExtractor:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not configured in settings or environment.")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

    async def extract_from_image_bytes(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg"
    ) -> FinancialFormData:
        return await _GeminiFinancialFormExtractor_extract_from_image_bytes_impl(self, image_bytes, mime_type)

    def _build_financial_form(self, data: Dict[str, Any]) -> FinancialFormData:
        """Builds and normalizes the FinancialFormData from parsed Gemini JSON."""
        final_date_str, day_of_week = self._parse_form_date(data.get("form_date"))
        attendance_items = self._build_attendance_items(data.get("attendance"))
        purchases_items = self._build_purchases(data.get("purchases"))
        expenses_items = self._build_expenses(data.get("expenses"))
        sales = self._build_sales(data.get("sales"))
        summary = self._build_summary(data.get("summary"))
        uncertainties = self._build_uncertainties(data.get("uncertainties"))
        form = FinancialFormData(
            form_date=final_date_str, day_of_week=day_of_week,
            attendance=attendance_items, purchases=purchases_items,
            expenses=expenses_items, sales=sales, summary=summary,
            ocr_uncertainties=uncertainties,
            all_uncertainties_resolved=len(uncertainties) == 0,
        )
        return recalculate_financial_form(form)

    @staticmethod
    def _parse_form_date(form_date_str: Any) -> tuple[str, str]:
        if form_date_str:
            try:
                date_obj, derived_weekday = parse_and_validate_form_date(form_date_str)
                return date_obj.strftime("%Y-%m-%d"), derived_weekday
            except Exception:
                pass
        today = get_current_amman_date()
        return today.strftime("%Y-%m-%d"), get_arabic_weekday(today)

    @staticmethod
    def _build_attendance_items(raw_attendance: Any) -> List[EmployeeAttendanceItem]:
        attendance_items: List[EmployeeAttendanceItem] = []
        for att in raw_attendance or []:
            status = att.get("status", "حاضر")
            entry = att.get("entry_time")
            exit_ = att.get("exit_time")
            duration = calculate_work_duration(entry, exit_, status)
            attendance_items.append(
                EmployeeAttendanceItem(
                    employee_name=att.get("employee_name", ""),
                    status=status if status in ["حاضر", "غائب", "إجازة", "مغادرة"] else "حاضر",
                    entry_time=entry,
                    exit_time=exit_,
                    duration_hours=duration,
                    notes=att.get("notes", ""),
                )
            )

        # Ensure minimum row count from config
        while len(attendance_items) < settings.EMPLOYEES_ROW_COUNT:
            attendance_items.append(EmployeeAttendanceItem())
        return attendance_items

    @staticmethod
    def _build_purchases(raw_purchases: Any) -> List[PurchaseItem]:
        purchases_items: List[PurchaseItem] = []
        for p in raw_purchases or []:
            try:
                amt = Decimal(str(p.get("amount", 0)))
            except Exception:
                amt = Decimal("0.00")
            purchases_items.append(
                PurchaseItem(
                    item=p.get("item", ""),
                    amount=amt,
                    invoice_number=p.get("invoice_number", ""),
                    notes=p.get("notes", ""),
                )
            )
        while len(purchases_items) < settings.PURCHASES_ROW_COUNT:
            purchases_items.append(PurchaseItem())
        return purchases_items

    @staticmethod
    def _build_expenses(raw_expenses: Any) -> List[ExpenseItem]:
        expenses_items: List[ExpenseItem] = []
        for e in raw_expenses or []:
            try:
                amt = Decimal(str(e.get("amount", 0)))
            except Exception:
                amt = Decimal("0.00")
            expenses_items.append(
                ExpenseItem(
                    item=e.get("item", ""),
                    amount=amt,
                    notes=e.get("notes", ""),
                )
            )
        while len(expenses_items) < settings.EXPENSES_ROW_COUNT:
            expenses_items.append(ExpenseItem())
        return expenses_items

    def _build_sales(self, raw_sales: Any) -> SalesData:
        raw_sales = raw_sales or {}
        return SalesData(
            sales=self._to_decimal(raw_sales.get("sales")),
            returns=self._to_decimal(raw_sales.get("returns")),
            orders=self._to_decimal(raw_sales.get("orders")),
            kareem=self._to_decimal(raw_sales.get("kareem")),
            ashaayi=self._to_decimal(raw_sales.get("ashaayi")),
            visa=self._to_decimal(raw_sales.get("visa")),
        )

    def _build_summary(self, raw_summary: Any) -> SummaryData:
        raw_summary = raw_summary or {}
        hw_bal = raw_summary.get("handwritten_current_balance")
        return SummaryData(
            total_purchases=self._to_decimal(raw_summary.get("total_purchases")),
            total_expenses=self._to_decimal(raw_summary.get("total_expenses")),
            previous_balance=self._to_decimal(raw_summary.get("previous_balance")),
            increase=self._to_decimal(raw_summary.get("increase")),
            decrease=self._to_decimal(raw_summary.get("decrease")),
            handwritten_current_balance=self._to_decimal(hw_bal) if hw_bal is not None else None,
        )

    @staticmethod
    def _build_uncertainties(raw_uncertainties: Any) -> List[OCRUncertainty]:
        uncertainties: List[OCRUncertainty] = []
        for u in raw_uncertainties or []:
            uncertainties.append(
                OCRUncertainty(
                    field_path=u.get("field_path", ""),
                    arabic_label=u.get("arabic_label", ""),
                    raw_extracted_text=u.get("raw_extracted_text", ""),
                    normalized_value=u.get("normalized_value"),
                    confidence=float(u.get("confidence", 0.5)),
                    reason=u.get("reason", "قراءة غير مؤكدة"),
                    resolved=False,
                )
            )
        return uncertainties

    def _to_decimal(self, val: Any) -> Decimal:
        if val is None or val == "":
            return Decimal("0.00")
        try:
            return Decimal(str(val)).quantize(Decimal("0.01"))
        except Exception:
            return Decimal("0.00")

exec('async def _GeminiFinancialFormExtractor_extract_from_image_bytes_impl(\n    self,\n    image_bytes: bytes,\n    mime_type: str = "image/jpeg"\n) -> FinancialFormData:\n    """\n    Calls Gemini API with the document image and converts structured response\n    into FinancialFormData with deterministic calculations.\n    """\n    if not self.client:\n        raise RuntimeError(\n            "Gemini API key is not configured. Please set GEMINI_API_KEY in your environment."\n        )\n    candidate_models = [self.model] if self.model else []\n    fallback_models = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.7-flash"]\n    for m in fallback_models:\n        if m and m not in candidate_models:\n            candidate_models.append(m)\n    last_error = None\n    for current_model in candidate_models:\n        logger.info(f"Submitting image ({len(image_bytes)} bytes, {mime_type}) to Gemini model: {current_model}")\n        try:\n            response = self.client.models.generate_content(\n                model=current_model,\n                contents=[\n                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),\n                    GEMINI_PROMPT,\n                ],\n                config=types.GenerateContentConfig(\n                    response_mime_type="application/json",\n                    temperature=0.1,\n                ),\n            )\n            raw_text = response.text\n            if not raw_text:\n                raise ValueError(f"Empty response received from Gemini model {current_model}.")\n            cleaned_text = raw_text.strip()\n            if cleaned_text.startswith("```"):\n                cleaned_text = cleaned_text.split("\\n", 1)[-1]\n            if cleaned_text.endswith("```"):\n                cleaned_text = cleaned_text.rsplit("\\n", 1)[0]\n            cleaned_text = cleaned_text.strip()\n            data = json.loads(cleaned_text)\n            return self._build_financial_form(data)\n        except Exception as e:\n            logger.warning(f"Gemini model {current_model} call failed ({type(e).__name__}): {e}")\n            last_error = e\n            continue\n    logger.error(f"All candidate Gemini models failed. Last error: {last_error}", exc_info=True)\n    raise last_error\n', globals())
