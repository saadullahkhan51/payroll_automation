from dataclasses import dataclass, field
from datetime import date
from typing import List, Dict, Any
from decimal import Decimal

@dataclass
class TaxInfo:
    """Tax information"""
    tax_card_type: str
    base_tax_rate: Decimal
    additional_tax_rate: Decimal
    income_limit_year: Decimal
    earnings_period_start: Decimal

@dataclass
class SalaryItem:
    """Individual salary item"""
    code: str
    description: str
    quantity: Decimal
    rate: Decimal
    total: Decimal

@dataclass
class Deduction:
    """Salary deduction"""
    code: str
    description: str
    amount: Decimal

@dataclass
class PayrollRecord:
    """Complete payroll record for an employee"""
    employee_id: str
    name: str
    address: str
    pay_period_start: date
    pay_period_end: date
    payment_date: date
    bank_details: str
    tax_info: TaxInfo
    salary_items: List[SalaryItem] = field(default_factory=list)
    deductions: List[Deduction] = field(default_factory=list)
    benefits: List[SalaryItem] = field(default_factory=list)
    tax_withholding: Decimal = Decimal('0')
    pension_insurance: Decimal = Decimal('0')
    health_insurance_daily: Decimal = Decimal('0')
    tax_free_portion: Decimal = Decimal('0')
    net_payment: Decimal = Decimal('0')
    gross_salary: Decimal = Decimal('0')
    year_to_date_gross: Decimal = Decimal('0')
    year_to_date_tax_free: Decimal = Decimal('0')
