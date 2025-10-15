from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Any
import random
from models.payroll import PayrollRecord, TaxInfo, SalaryItem, Deduction

class MockLikeitAPI:
    """Mock API for Likeit accounting software"""
    
    # Sample employee data
    MOCK_EMPLOYEES = [
        {
            "employee_id": "01012020-123X",
            "name": "Sam Sample",
            "address": "Mechelininkatu 10, 00100 Helsinki",
            "bank_details": "IBAN: FI12 3456 7890 1234 56, BIC: NDEAFIHH"
        },
        {
            "employee_id": "15031985-456Y",
            "name": "Maria Mäkinen",
            "address": "Kalevankatu 5, 00100 Helsinki",
            "bank_details": "IBAN: FI98 7654 3210 9876 54, BIC: OKOYFIHH"
        },
        {
            "employee_id": "22071992-789Z",
            "name": "Jukka Virtanen",
            "address": "Mannerheimintie 20, 00100 Helsinki",
            "bank_details": "IBAN: FI45 1122 3344 5566 77, BIC: HANDFIHH"
        }
    ]
    
    def __init__(self):
        self.base_hourly_rate = Decimal('17.00')
        self.evening_supplement_rate = Decimal('1.41')
        self.per_diem_rate = Decimal('68.00')
        self.travel_compensation = Decimal('600.00')
    
    def get_monthly_payroll(self, year: int, month: int) -> List[PayrollRecord]:
        """Get payroll data for all employees for a given month"""
        records = []
        
        for emp in self.MOCK_EMPLOYEES:
            record = self._generate_payroll_record(emp, year, month)
            records.append(record)
        
        return records
    
    def get_employee_payroll(self, employee_id: str, year: int, month: int) -> PayrollRecord:
        """Get payroll data for a specific employee"""
        employee = next((e for e in self.MOCK_EMPLOYEES if e['employee_id'] == employee_id), None)
        
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")
        
        return self._generate_payroll_record(employee, year, month)
    
    def _generate_payroll_record(self, employee: Dict, year: int, month: int) -> PayrollRecord:
        """Generate a payroll record with realistic data"""
        
        # Calculate period dates
        pay_period_start = date(year, month, 1)
        if month == 12:
            pay_period_end = date(year, month, 31)
            payment_date = date(year + 1, 1, 15)
        else:
            next_month = date(year, month + 1, 1)
            pay_period_end = next_month - timedelta(days=1)
            payment_date = date(year, month, 25)
        
        # Generate salary items
        regular_hours = Decimal(str(random.uniform(60, 80)))
        overtime_hours = Decimal(str(random.uniform(0, 10)))
        overtime_50_hours = Decimal(str(random.uniform(0, 5)))
        evening_hours = Decimal(str(random.uniform(5, 15)))
        per_diem_days = Decimal(str(random.randint(5, 12)))
        
        salary_items = [
            SalaryItem(
                code="12101",
                description="Aikatyö",
                quantity=regular_hours,
                rate=self.base_hourly_rate,
                total=regular_hours * self.base_hourly_rate
            ),
            SalaryItem(
                code="12101_2",
                description="Aikatyö YT",
                quantity=overtime_hours,
                rate=self.base_hourly_rate,
                total=overtime_hours * self.base_hourly_rate
            ),
            SalaryItem(
                code="12102",
                description="Ylityö 50%",
                quantity=overtime_50_hours,
                rate=self.base_hourly_rate * Decimal('0.5'),
                total=overtime_50_hours * self.base_hourly_rate * Decimal('0.5')
            ),
            SalaryItem(
                code="12107",
                description="Iltalisä",
                quantity=evening_hours,
                rate=self.evening_supplement_rate,
                total=evening_hours * self.evening_supplement_rate
            )
        ]
        
        # Calculate gross from salary items
        gross_from_salary = sum(item.total for item in salary_items)
        
        # Benefits
        benefits = [
            SalaryItem(
                code="MK002",
                description="Matkakorvaus verotettava — Elokuu",
                quantity=Decimal('1.00'),
                rate=self.travel_compensation,
                total=self.travel_compensation
            ),
            SalaryItem(
                code="PVR003",
                description="Ulkomaan päiväraha",
                quantity=per_diem_days,
                rate=self.per_diem_rate,
                total=per_diem_days * self.per_diem_rate
            )
        ]
        
        # Tax-free portion (per diem has tax-free component)
        tax_free_portion = per_diem_days * self.per_diem_rate
        
        # Total taxable income
        gross_salary = gross_from_salary + self.travel_compensation
        
        # Calculate Swedish tax (30% on income above threshold)
        swedish_tax_threshold = Decimal('20727.88')
        taxable_in_sweden = gross_salary - swedish_tax_threshold
        swedish_tax_amount = Decimal('0')
        swedish_tax_deduction = Decimal('0')
        
        if taxable_in_sweden > 0:
            swedish_tax_amount = -(taxable_in_sweden * Decimal('0.30'))
            swedish_tax_deduction = -(Decimal('217.78'))  # Standard deduction
        
        # Deductions
        deductions = []
        
        if swedish_tax_amount < 0:
            deductions.extend([
                Deduction(
                    code="VÄH",
                    description="Vähennys palkasta — Ruotsin verot 30% verotettavasta tulosta SEK 20 727,88",
                    amount=swedish_tax_amount
                ),
                Deduction(
                    code="VÄH",
                    description="Vähennys palkasta — Ruotsin verot 30% verotettavista kulukorvauksista SEK 4 217,78",
                    amount=swedish_tax_deduction
                )
            ])
        
        # Finnish tax withholding
        base_tax_rate = Decimal('16.50')
        additional_tax_rate = Decimal('44.00')
        income_limit = Decimal('39800.00')
        
        # Calculate year-to-date (simulate progressive accumulation)
        month_multiplier = month
        ytd_gross = gross_salary * Decimal(str(month_multiplier))
        ytd_tax_free = tax_free_portion * Decimal(str(month_multiplier))
        
        # Calculate tax withholding
        if ytd_gross <= income_limit:
            finnish_tax = -(gross_salary * base_tax_rate / Decimal('100'))
        else:
            finnish_tax = -(gross_salary * additional_tax_rate / Decimal('100'))
        
        # Other deductions
        pension_insurance = -(gross_salary * Decimal('0.0715'))  # 7.15% TyEL
        health_insurance = gross_salary * Decimal('0.0084')  # 0.84% daily allowance
        
        deductions.extend([
            Deduction(
                code="ENNPID",
                description="Ennakonpidätys (Suomen verokortin poisto)",
                amount=Decimal('0')  # Reduced to 0 because of Swedish tax
            )
        ])
        
        # Calculate net payment
        total_deductions = sum(d.amount for d in deductions) + pension_insurance
        net_payment = gross_salary + total_deductions
        
        # Tax info
        tax_info = TaxInfo(
            tax_card_type="Perus",
            base_tax_rate=base_tax_rate,
            additional_tax_rate=additional_tax_rate,
            income_limit_year=income_limit,
            earnings_period_start=ytd_gross
        )
        
        # Create payroll record
        record = PayrollRecord(
            employee_id=employee['employee_id'],
            name=employee['name'],
            address=employee['address'],
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end,
            payment_date=payment_date,
            bank_details=employee['bank_details'],
            tax_info=tax_info,
            salary_items=salary_items,
            deductions=deductions,
            benefits=benefits,
            tax_withholding=finnish_tax,
            pension_insurance=pension_insurance,
            health_insurance_daily=health_insurance,
            tax_free_portion=tax_free_portion,
            net_payment=net_payment,
            gross_salary=gross_salary,
            year_to_date_gross=ytd_gross,
            year_to_date_tax_free=ytd_tax_free
        )
        
        return record
    
    def get_all_employees(self) -> List[Dict[str, str]]:
        """Get list of all employees"""
        return self.MOCK_EMPLOYEES.copy()
