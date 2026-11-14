"""
Pydantic schemas for Project # hasep Arabic Handwritten Financial Form.
Uses Python Decimal for financial integrity with 2 decimal places.
"""

from decimal import Decimal
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator
import datetime


def round_decimal(val: Optional[Decimal]) -> Decimal:
    if val is None:
        return Decimal("0.00")
    return Decimal(str(val)).quantize(Decimal("0.01"))


class EmployeeAttendanceItem(BaseModel):
    employee_name: str = ""
    status: Literal["حاضر", "غائب", "إجازة", "مغادرة", ""] = "حاضر"
    entry_time: Optional[str] = None  # "HH:MM" 24h or 12h
    exit_time: Optional[str] = None   # "HH:MM"
    duration_hours: Decimal = Field(default=Decimal("0.00"))
    notes: Optional[str] = ""

    @field_validator("duration_hours", mode="before")
    def validate_duration(cls, v):
        return round_decimal(v)


class PurchaseItem(BaseModel):
    item: str = ""
    amount: Decimal = Field(default=Decimal("0.00"))
    invoice_number: Optional[str] = ""
    notes: Optional[str] = ""

    @field_validator("amount", mode="before")
    def validate_amount(cls, v):
        return round_decimal(v)


class ExpenseItem(BaseModel):
    item: str = ""
    amount: Decimal = Field(default=Decimal("0.00"))
    notes: Optional[str] = ""

    @field_validator("amount", mode="before")
    def validate_amount(cls, v):
        return round_decimal(v)


class SalesData(BaseModel):
    sales: Decimal = Field(default=Decimal("0.00"))
    returns: Decimal = Field(default=Decimal("0.00"))
    net_sale: Decimal = Field(default=Decimal("0.00"))
    orders: Decimal = Field(default=Decimal("0.00"))
    kareem: Decimal = Field(default=Decimal("0.00"))
    ashaayi: Decimal = Field(default=Decimal("0.00"))
    visa: Decimal = Field(default=Decimal("0.00"))
    total_applications: Decimal = Field(default=Decimal("0.00"))
    total_sale: Decimal = Field(default=Decimal("0.00"))

    @field_validator(
        "sales", "returns", "net_sale", "orders", "kareem", "ashaayi", "visa",
        "total_applications", "total_sale", mode="before"
    )
    def validate_decimals(cls, v):
        return round_decimal(v)


class SummaryData(BaseModel):
    total_expenses: Decimal = Field(default=Decimal("0.00"))
    total_purchases: Decimal = Field(default=Decimal("0.00"))
    total_expenses_and_purchases: Decimal = Field(default=Decimal("0.00"))
    previous_balance: Decimal = Field(default=Decimal("0.00"))
    increase: Decimal = Field(default=Decimal("0.00"))
    decrease: Decimal = Field(default=Decimal("0.00"))
    current_balance: Decimal = Field(default=Decimal("0.00"))
    handwritten_current_balance: Optional[Decimal] = None

    @field_validator(
        "total_expenses", "total_purchases", "total_expenses_and_purchases",
        "previous_balance", "increase", "decrease", "current_balance", mode="before"
    )
    def validate_decimals(cls, v):
        return round_decimal(v)

    @field_validator("handwritten_current_balance", mode="before")
    def validate_optional_decimals(cls, v):
        if v is None or v == "":
            return None
        return round_decimal(v)


class CalculationMismatch(BaseModel):
    equation_id: str
    field_name: str
    arabic_label: str
    extracted_value: Optional[Decimal] = None
    calculated_value: Decimal
    difference: Decimal
    severity: Literal["error", "warning"] = "error"
    message: str


class OCRUncertainty(BaseModel):
    field_path: str
    arabic_label: str
    raw_extracted_text: Optional[str] = ""
    normalized_value: Any = None
    confidence: float = 1.0  # 0.0 - 1.0
    reason: str = ""
    resolved: bool = False


class FinancialFormData(BaseModel):
    form_date: str  # YYYY-MM-DD
    day_of_week: str  # derived Arabic weekday
    attendance: List[EmployeeAttendanceItem] = []
    purchases: List[PurchaseItem] = []
    expenses: List[ExpenseItem] = []
    sales: SalesData = Field(default_factory=SalesData)
    summary: SummaryData = Field(default_factory=SummaryData)

    # Discrepancy & Verification metadata
    calculation_mismatches: List[CalculationMismatch] = []
    ocr_uncertainties: List[OCRUncertainty] = []
    is_mathematically_valid: bool = True
    all_uncertainties_resolved: bool = False


class FieldUpdatePayload(BaseModel):
    field_path: str  # e.g., "sales.orders" or "purchases.0.amount" or "attendance.1.entry_time"
    value: Any


class ResolveUncertaintyPayload(BaseModel):
    field_path: str
    confirmed_value: Any


class FormApprovalPayload(BaseModel):
    notes: Optional[str] = None
    force_override_mismatches: bool = False
