from sqlalchemy import Column, Integer, String, Date, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

class EmployeeDB(Base):
    """Employee database model"""
    __tablename__ = "employees"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String)
    bank_details = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    payroll_records = relationship("PayrollRecordDB", back_populates="employee")
    
    def __repr__(self):
        return f"<Employee(id={self.id}, name={self.name})>"


class PayrollRecordDB(Base):
    """Payroll record database model"""
    __tablename__ = "payroll_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String, ForeignKey('employees.id'), nullable=False)
    
    # Period information
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)
    pay_period_start = Column(Date, nullable=False)
    pay_period_end = Column(Date, nullable=False)
    payment_date = Column(Date, nullable=False)
    
    # Financial totals
    gross_salary = Column(Numeric(10, 2), nullable=False)
    net_payment = Column(Numeric(10, 2), nullable=False)
    
    # Tax information
    swedish_tax = Column(Numeric(10, 2), default=0)
    finnish_tax_withholding = Column(Numeric(10, 2), default=0)
    tax_free_portion = Column(Numeric(10, 2), default=0)
    
    # Insurance and deductions
    pension_insurance = Column(Numeric(10, 2), default=0)
    health_insurance = Column(Numeric(10, 2), default=0)
    
    # Year-to-date tracking
    ytd_gross = Column(Numeric(10, 2), default=0)
    ytd_tax_free = Column(Numeric(10, 2), default=0)
    
    # Detailed data stored as JSON
    data_json = Column(Text, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = relationship("EmployeeDB", back_populates="payroll_records")
    salary_items = relationship("SalaryItemDB", back_populates="payroll_record", cascade="all, delete-orphan")
    deductions = relationship("DeductionDB", back_populates="payroll_record", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<PayrollRecord(id={self.id}, employee={self.employee_id}, period={self.year}-{self.month:02d})>"


class SalaryItemDB(Base):
    """Individual salary item database model"""
    __tablename__ = "salary_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    payroll_record_id = Column(Integer, ForeignKey('payroll_records.id'), nullable=False)
    
    # Item details
    code = Column(String(20), nullable=False)
    description = Column(String(255), nullable=False)
    quantity = Column(Numeric(10, 2))
    rate = Column(Numeric(10, 2))
    total = Column(Numeric(10, 2), nullable=False)
    
    # Type classification
    item_type = Column(String(20))  # 'salary', 'overtime', 'supplement', 'benefit'
    
    # Relationships
    payroll_record = relationship("PayrollRecordDB", back_populates="salary_items")
    
    def __repr__(self):
        return f"<SalaryItem(code={self.code}, description={self.description}, total={self.total})>"


class DeductionDB(Base):
    """Deduction database model"""
    __tablename__ = "deductions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    payroll_record_id = Column(Integer, ForeignKey('payroll_records.id'), nullable=False)
    
    # Deduction details
    code = Column(String(20), nullable=False)
    description = Column(String(255), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    
    # Type classification
    deduction_type = Column(String(20))  # 'tax', 'insurance', 'other'
    
    # Relationships
    payroll_record = relationship("PayrollRecordDB", back_populates="deductions")
    
    def __repr__(self):
        return f"<Deduction(code={self.code}, description={self.description}, amount={self.amount})>"


class TaxFormSubmissionDB(Base):
    """Track tax form submissions"""
    __tablename__ = "tax_form_submissions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Form information
    form_type = Column(String(20), nullable=False)  # 'SKV4788', 'SKV4786'
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    employee_id = Column(String, ForeignKey('employees.id'))  # NULL for combined forms
    
    # Submission details
    submission_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default='pending')  # 'pending', 'submitted', 'accepted', 'rejected'
    reference_number = Column(String(100))
    
    # File paths
    form_file_path = Column(String(500))
    
    # Response data
    response_json = Column(Text)
    
    def __repr__(self):
        return f"<TaxFormSubmission(id={self.id}, type={self.form_type}, status={self.status})>"


class AnnualSummaryDB(Base):
    """Annual summary for employees"""
    __tablename__ = "annual_summaries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String, ForeignKey('employees.id'), nullable=False)
    year = Column(Integer, nullable=False, index=True)
    
    # Annual totals
    total_gross_salary = Column(Numeric(10, 2), nullable=False)
    total_net_payment = Column(Numeric(10, 2), nullable=False)
    total_swedish_tax = Column(Numeric(10, 2), default=0)
    total_finnish_tax = Column(Numeric(10, 2), default=0)
    total_pension_insurance = Column(Numeric(10, 2), default=0)
    total_health_insurance = Column(Numeric(10, 2), default=0)
    total_tax_free_portion = Column(Numeric(10, 2), default=0)
    
    # Working time statistics
    total_regular_hours = Column(Numeric(10, 2), default=0)
    total_overtime_hours = Column(Numeric(10, 2), default=0)
    
    # Generated files
    summary_file_path = Column(String(500))
    
    # Metadata
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<AnnualSummary(employee={self.employee_id}, year={self.year})>"
