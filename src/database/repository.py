from sqlalchemy.orm import Session
from sqlalchemy import and_, extract, func
from typing import List, Optional
from datetime import date
import json
from .models import (
    EmployeeDB, PayrollRecordDB, SalaryItemDB, 
    DeductionDB, TaxFormSubmissionDB, AnnualSummaryDB
)
from models.payroll import PayrollRecord, SalaryItem, Deduction
from models.employee import Employee

class PayrollRepository:
    """Repository for payroll data operations"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    # ========== Employee Operations ==========
    
    def save_employee(self, employee: Employee) -> EmployeeDB:
        """Save or update employee"""
        db_employee = self.db.query(EmployeeDB).filter_by(id=employee.employee_id).first()
        if not db_employee:
            db_employee = EmployeeDB(
                id=employee.employee_id,
                name=employee.name,
                address=employee.address,
                bank_details=employee.bank_details
            )
            self.db.add(db_employee)
        else:
            db_employee.name = employee.name
            db_employee.address = employee.address
            db_employee.bank_details = employee.bank_details
        self.db.commit()
        self.db.refresh(db_employee)
        return db_employee
    
    def get_employee(self, employee_id: str) -> Optional[EmployeeDB]:
        """Get employee by ID"""
        return self.db.query(EmployeeDB).filter_by(id=employee_id).first()
    
    def get_all_employees(self) -> List[EmployeeDB]:
        """Get all employees"""
        return self.db.query(EmployeeDB).all()
    
    # ========== Payroll Record Operations ==========
    
    def save_payroll_record(self, payroll_record: PayrollRecord) -> PayrollRecordDB:
        """Save complete payroll record with items and deductions"""
        
        # Calculate Swedish tax from deductions
        swedish_tax = sum(
            abs(float(d.amount)) for d in payroll_record.deductions 
            if 'Swedish' in d.description or 'Ruotsin' in d.description
        )
        
        # Create payroll record
        record = PayrollRecordDB(
            employee_id=payroll_record.employee_id,
            year=payroll_record.pay_period_start.year,
            month=payroll_record.pay_period_start.month,
            pay_period_start=payroll_record.pay_period_start,
            pay_period_end=payroll_record.pay_period_end,
            payment_date=payroll_record.payment_date,
            gross_salary=float(payroll_record.gross_salary),
            net_payment=float(payroll_record.net_payment),
            swedish_tax=swedish_tax,
            finnish_tax_withholding=float(payroll_record.tax_withholding),
            tax_free_portion=float(payroll_record.tax_free_portion),
            pension_insurance=float(payroll_record.pension_insurance),
            health_insurance=float(payroll_record.health_insurance_daily),
            ytd_gross=float(payroll_record.year_to_date_gross),
            ytd_tax_free=float(payroll_record.year_to_date_tax_free),
            data_json=json.dumps({
                'tax_info': {
                    'tax_card_type': payroll_record.tax_info.tax_card_type,
                    'base_tax_rate': str(payroll_record.tax_info.base_tax_rate),
                    'additional_tax_rate': str(payroll_record.tax_info.additional_tax_rate),
                    'income_limit_year': str(payroll_record.tax_info.income_limit_year),
                }
            })
        )
        self.db.add(record)
        self.db.flush()  # Get the ID
        
        # Add salary items
        for item in payroll_record.salary_items:
            salary_item = SalaryItemDB(
                payroll_record_id=record.id,
                code=item.code,
                description=item.description,
                quantity=float(item.quantity) if item.quantity else None,
                rate=float(item.rate) if item.rate else None,
                total=float(item.total),
                item_type=self._classify_salary_item(item.code)
            )
            self.db.add(salary_item)
        
        # Add benefits as salary items
        for benefit in payroll_record.benefits:
            salary_item = SalaryItemDB(
                payroll_record_id=record.id,
                code=benefit.code,
                description=benefit.description,
                quantity=float(benefit.quantity) if benefit.quantity else None,
                rate=float(benefit.rate) if benefit.rate else None,
                total=float(benefit.total),
                item_type='benefit'
            )
            self.db.add(salary_item)
        
        # Add deductions
        for deduction in payroll_record.deductions:
            deduction_item = DeductionDB(
                payroll_record_id=record.id,
                code=deduction.code,
                description=deduction.description,
                amount=float(deduction.amount),
                deduction_type=self._classify_deduction(deduction.code, deduction.description)
            )
            self.db.add(deduction_item)
        
        self.db.commit()
        self.db.refresh(record)
        return record
    
    def get_payroll_record(self, employee_id: str, year: int, month: int) -> Optional[PayrollRecordDB]:
        """Get specific payroll record"""
        return self.db.query(PayrollRecordDB).filter(
            and_(
                PayrollRecordDB.employee_id == employee_id,
                PayrollRecordDB.year == year,
                PayrollRecordDB.month == month
            )
        ).first()
    
    def get_payroll_records(self, employee_id: str, year: Optional[int] = None) -> List[PayrollRecordDB]:
        """Get payroll records for employee"""
        query = self.db.query(PayrollRecordDB).filter_by(employee_id=employee_id)
        if year:
            query = query.filter_by(year=year)
        return query.order_by(PayrollRecordDB.year, PayrollRecordDB.month).all()
    
    def get_monthly_records(self, year: int, month: int) -> List[PayrollRecordDB]:
        """Get all payroll records for a specific month"""
        return self.db.query(PayrollRecordDB).filter(
            and_(
                PayrollRecordDB.year == year,
                PayrollRecordDB.month == month
            )
        ).all()
    
    # ========== Tax Form Submission Operations ==========
    
    def save_tax_form_submission(self, form_type: str, year: int, month: int, 
                                employee_id: Optional[str], file_path: str) -> TaxFormSubmissionDB:
        """Save tax form submission record"""
        submission = TaxFormSubmissionDB(
            form_type=form_type,
            year=year,
            month=month,
            employee_id=employee_id,
            form_file_path=file_path,
            status='pending'
        )
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)
        return submission
    
    def update_submission_status(self, submission_id: int, status: str, 
                                reference_number: Optional[str] = None,
                                response_data: Optional[dict] = None):
        """Update tax form submission status"""
        submission = self.db.query(TaxFormSubmissionDB).filter_by(id=submission_id).first()
        if submission:
            submission.status = status
            if reference_number:
                submission.reference_number = reference_number
            if response_data:
                submission.response_json = json.dumps(response_data)
            self.db.commit()
    
    # ========== Annual Summary Operations ==========
    
    def create_annual_summary(self, employee_id: str, year: int) -> AnnualSummaryDB:
        """Create annual summary from payroll records"""
        records = self.get_payroll_records(employee_id, year)
        
        if not records:
            return None
        
        # Calculate totals
        total_gross = sum(r.gross_salary for r in records)
        total_net = sum(r.net_payment for r in records)
        total_swedish_tax = sum(r.swedish_tax for r in records)
        total_finnish_tax = sum(r.finnish_tax_withholding for r in records)
        total_pension = sum(r.pension_insurance for r in records)
        total_health = sum(r.health_insurance for r in records)
        total_tax_free = sum(r.tax_free_portion for r in records)
        
        # Calculate hours (from salary items)
        total_regular = 0
        total_overtime = 0
        for record in records:
            for item in record.salary_items:
                if item.code.startswith('12101') and '_' not in item.code:
                    total_regular += float(item.quantity) if item.quantity else 0
                elif 'overtime' in item.description.lower() or 'ylityö' in item.description.lower():
                    total_overtime += float(item.quantity) if item.quantity else 0
        
        summary = AnnualSummaryDB(
            employee_id=employee_id,
            year=year,
            total_gross_salary=total_gross,
            total_net_payment=total_net,
            total_swedish_tax=total_swedish_tax,
            total_finnish_tax=total_finnish_tax,
            total_pension_insurance=total_pension,
            total_health_insurance=total_health,
            total_tax_free_portion=total_tax_free,
            total_regular_hours=total_regular,
            total_overtime_hours=total_overtime
        )
        
        self.db.add(summary)
        self.db.commit()
        self.db.refresh(summary)
        return summary
    
    def get_annual_summary(self, employee_id: str, year: int) -> Optional[AnnualSummaryDB]:
        """Get annual summary"""
        return self.db.query(AnnualSummaryDB).filter(
            and_(
                AnnualSummaryDB.employee_id == employee_id,
                AnnualSummaryDB.year == year
            )
        ).first()
    
    # ========== Helper Methods ==========
    
    def _classify_salary_item(self, code: str) -> str:
        """Classify salary item by code"""
        if code.startswith('12101'):
            return 'salary'
        elif code.startswith('12102'):
            return 'overtime'
        elif code.startswith('12107'):
            return 'supplement'
        elif code.startswith('MK') or code.startswith('PVR'):
            return 'benefit'
        return 'other'
    
    def _classify_deduction(self, code: str, description: str) -> str:
        """Classify deduction type"""
        if 'tax' in description.lower() or 'vero' in description.lower():
            return 'tax'
        elif 'insurance' in description.lower() or 'vakuutus' in description.lower():
            return 'insurance'
        return 'other'