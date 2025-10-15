import sys
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from database.db import engine, Base, SessionLocal
from database.repository import PayrollRepository
from models.employee import Employee
from models.payroll import PayrollRecord, TaxInfo, SalaryItem, Deduction
import random

def get_pay_periods_for_month(year: int, month: int):
    """
    Calculate 2-week pay periods for a month
    Returns list of (start_date, end_date, payment_date) tuples
    """
    periods = []
    
    # First period: 1st-14th, paid on 20th
    start_1 = date(year, month, 1)
    end_1 = date(year, month, 14)
    pay_1 = date(year, month, 20)
    periods.append((start_1, end_1, pay_1))
    
    # Second period: 15th-last day, paid on 5th of next month
    start_2 = date(year, month, 15)
    
    # Calculate last day of month
    if month == 12:
        end_2 = date(year, 12, 31)
        pay_2 = date(year + 1, 1, 5)
    else:
        # Get first day of next month, then subtract one day
        next_month = date(year, month + 1, 1)
        end_2 = next_month - timedelta(days=1)
        pay_2 = date(year, month + 1, 5)
    
    periods.append((start_2, end_2, pay_2))
    
    return periods

def create_realistic_payroll_record(employee: dict, year: int, month: int, 
                                   period_start: date, period_end: date, 
                                   payment_date: date, ytd_accumulator: dict) -> PayrollRecord:
    """Create a realistic payroll record for an employee"""
    
    # Calculate working days (approximately 10 days per 2-week period)
    working_days = (period_end - period_start).days + 1
    
    # Random variation in hours worked
    base_hours = working_days * 8 * random.uniform(0.85, 1.0)  # 8h/day with variance
    regular_hours = Decimal(str(round(base_hours, 2)))
    
    # Overtime (20-30% of employees work overtime)
    overtime_hours = Decimal(str(round(random.uniform(0, 15), 2))) if random.random() > 0.7 else Decimal('0')
    overtime_50_hours = Decimal(str(round(random.uniform(0, 8), 2))) if random.random() > 0.8 else Decimal('0')
    
    # Evening work (about 30% of workers)
    evening_hours = Decimal(str(round(random.uniform(5, 20), 2))) if random.random() > 0.7 else Decimal('0')
    
    # Per diem (about 60% of workers get per diem)
    per_diem_days = random.randint(5, 10) if random.random() > 0.4 else 0
    
    # Rates
    hourly_rate = Decimal('17.00')
    evening_supplement = Decimal('1.41')
    per_diem_rate = Decimal('68.00')
    travel_compensation = Decimal('600.00') if per_diem_days > 0 else Decimal('0')
    
    # Salary items
    salary_items = [
        SalaryItem(
            code="12101",
            description="Aikatyö (Regular work)",
            quantity=regular_hours,
            rate=hourly_rate,
            total=regular_hours * hourly_rate
        )
    ]
    
    if overtime_hours > 0:
        salary_items.append(SalaryItem(
            code="12101_2",
            description="Aikatyö YT (Overtime)",
            quantity=overtime_hours,
            rate=hourly_rate,
            total=overtime_hours * hourly_rate
        ))
    
    if overtime_50_hours > 0:
        salary_items.append(SalaryItem(
            code="12102",
            description="Ylityö 50% (50% overtime bonus)",
            quantity=overtime_50_hours,
            rate=hourly_rate * Decimal('0.5'),
            total=overtime_50_hours * hourly_rate * Decimal('0.5')
        ))
    
    if evening_hours > 0:
        salary_items.append(SalaryItem(
            code="12107",
            description="Iltalisä (Evening supplement)",
            quantity=evening_hours,
            rate=evening_supplement,
            total=evening_hours * evening_supplement
        ))
    
    # Calculate gross salary from work
    gross_from_work = sum(item.total for item in salary_items)
    
    # Benefits (non-taxable in Finland, but reported)
    benefits = []
    tax_free_portion = Decimal('0')
    
    if per_diem_days > 0:
        per_diem_total = Decimal(str(per_diem_days)) * per_diem_rate
        benefits.append(SalaryItem(
            code="PVR003",
            description="Ulkomaan päiväraha (Foreign per diem)",
            quantity=Decimal(str(per_diem_days)),
            rate=per_diem_rate,
            total=per_diem_total
        ))
        tax_free_portion = per_diem_total
    
    if travel_compensation > 0:
        benefits.append(SalaryItem(
            code="MK002",
            description="Matkakorvaus verotettava (Taxable travel compensation)",
            quantity=Decimal('1.00'),
            rate=travel_compensation,
            total=travel_compensation
        ))
    
    # Total gross salary (including travel compensation)
    gross_salary = gross_from_work + travel_compensation
    
    # Swedish tax calculation (30% on taxable income)
    # Threshold is about 20,000 EUR annually, so about 1,667 EUR monthly, 833 per period
    swedish_tax_threshold = Decimal('833.00')
    taxable_in_sweden = gross_salary - swedish_tax_threshold
    
    deductions = []
    
    if taxable_in_sweden > 0:
        swedish_tax_on_income = -(taxable_in_sweden * Decimal('0.30'))
        swedish_tax_on_allowance = -(Decimal('217.78'))  # Standard deduction
        
        deductions.extend([
            Deduction(
                code="VÄH",
                description="Vähennys palkasta — Ruotsin verot 30% verotettavasta tulosta SEK 20 727,88",
                amount=swedish_tax_on_income
            ),
            Deduction(
                code="VÄH",
                description="Vähennys palkasta — Ruotsin verot 30% verotettavista kulukorvauksista SEK 4 217,78",
                amount=swedish_tax_on_allowance
            )
        ])
        total_swedish_tax = swedish_tax_on_income + swedish_tax_on_allowance
    else:
        total_swedish_tax = Decimal('0')
    
    # Finnish tax withholding (reduced because of Swedish tax)
    base_tax_rate = Decimal('16.50')
    finnish_tax = -(gross_salary * base_tax_rate / Decimal('100')) * Decimal('0.3')  # Reduced
    
    # Pension insurance (7.15% TyEL)
    pension_insurance = -(gross_salary * Decimal('0.0715'))
    
    # Health insurance daily allowance (0.84%)
    health_insurance = gross_salary * Decimal('0.0084')
    
    # Update year-to-date
    ytd_accumulator['gross'] += gross_salary
    ytd_accumulator['tax_free'] += tax_free_portion
    
    # Calculate net payment
    total_deductions = sum(d.amount for d in deductions) + pension_insurance + finnish_tax
    net_payment = gross_salary + total_deductions  # total_deductions is negative
    
    # Tax info
    tax_info = TaxInfo(
        tax_card_type="Perus",
        base_tax_rate=base_tax_rate,
        additional_tax_rate=Decimal('44.00'),
        income_limit_year=Decimal('39800.00'),
        earnings_period_start=ytd_accumulator['gross']
    )
    
    # Create payroll record
    record = PayrollRecord(
        employee_id=employee['employee_id'],
        name=employee['name'],
        address=employee['address'],
        pay_period_start=period_start,
        pay_period_end=period_end,
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
        year_to_date_gross=ytd_accumulator['gross'],
        year_to_date_tax_free=ytd_accumulator['tax_free']
    )
    
    return record

def reset_and_populate_database():
    """Reset database and populate with realistic test data"""
    
    print("=" * 80)
    print("DATABASE RESET AND POPULATION")
    print("=" * 80)
    
    # Step 1: Drop all tables
    print("\n1. Dropping all existing tables...")
    Base.metadata.drop_all(engine)
    print("   ✓ All tables dropped")
    
    # Step 2: Create all tables
    print("\n2. Creating fresh database schema...")
    Base.metadata.create_all(engine)
    print("   ✓ Database schema created")
    
    # Step 3: Create session and repository
    db = SessionLocal()
    repo = PayrollRepository(db)
    
    # Step 4: Define employees
    employees = [
        {
            "employee_id": "01011990-123A",
            "name": "Matti Virtanen",
            "address": "Mechelininkatu 10, 00100 Helsinki",
            "bank_details": "IBAN: FI21 1234 5600 0007 85, BIC: NDEAFIHH"
        },
        {
            "employee_id": "15061985-456B",
            "name": "Sanna Korhonen",
            "address": "Kalevankatu 15, 00100 Helsinki",
            "bank_details": "IBAN: FI98 7654 3210 9876 54, BIC: OKOYFIHH"
        },
        {
            "employee_id": "22121992-789C",
            "name": "Jukka Mäkinen",
            "address": "Mannerheimintie 20, 00100 Helsinki",
            "bank_details": "IBAN: FI45 1122 3344 5566 77, BIC: HANDFIHH"
        },
        {
            "employee_id": "08031988-234D",
            "name": "Liisa Saarinen",
            "address": "Aleksanterinkatu 5, 00100 Helsinki",
            "bank_details": "IBAN: FI67 8899 0011 2233 44, BIC: HELSFIHH"
        }
    ]
    
    print(f"\n3. Adding {len(employees)} employees...")
    for emp_data in employees:
        employee = Employee(
            employee_id=emp_data['employee_id'],
            name=emp_data['name'],
            address=emp_data['address'],
            bank_details=emp_data['bank_details']
        )
        repo.save_employee(employee)
        print(f"   ✓ Added: {emp_data['name']}")
    
    # Step 5: Generate payroll data for 6 months (Jan-Jun 2025)
    print("\n4. Generating payroll data for 6 months (Jan-Jun 2025)...")
    
    year = 2025
    total_records = 0
    
    for month in range(1, 7):  # January to June
        print(f"\n   Month {month:02d}/{year}:")
        
        # Get pay periods for this month
        periods = get_pay_periods_for_month(year, month)
        
        for period_idx, (start, end, payment) in enumerate(periods, 1):
            print(f"     Period {period_idx}: {start} to {end} (paid {payment})")
            
            # Generate records for each employee
            for emp_data in employees:
                # Initialize YTD accumulator for each employee (would persist across months in real scenario)
                if month == 1 and period_idx == 1:
                    ytd_accumulators = {emp['employee_id']: {'gross': Decimal('0'), 'tax_free': Decimal('0')} 
                                       for emp in employees}
                
                ytd = ytd_accumulators.get(emp_data['employee_id'], {'gross': Decimal('0'), 'tax_free': Decimal('0')})
                
                record = create_realistic_payroll_record(
                    emp_data, year, month, start, end, payment, ytd
                )
                
                repo.save_payroll_record(record)
                total_records += 1
            
            print(f"       ✓ Generated {len(employees)} records")
    
    print(f"\n   Total records created: {total_records}")
    
    # Step 6: Summary statistics
    print("\n5. Database Summary:")
    print(f"   • Employees: {len(employees)}")
    print(f"   • Months: 6 (Jan-Jun 2025)")
    print(f"   • Pay periods per month: 2")
    print(f"   • Total payroll records: {total_records}")
    print(f"   • Average records per employee: {total_records / len(employees):.0f}")
    
    db.close()
    
    print("\n" + "=" * 80)
    print("✓ DATABASE RESET AND POPULATION COMPLETE!")
    print("=" * 80)
    
    print("\nYou can now:")
    print("  1. Run the web app: python app.py")
    print("  2. Generate reports for any month from Jan-Jun 2025")
    print("  3. Test with realistic 2-week pay period data")
    print("  4. Each employee has varied hours, overtime, and per diem")

if __name__ == "__main__":
    reset_and_populate_database()