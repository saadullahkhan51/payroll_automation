import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from api.mock_likeit import MockLikeitAPI
from processors.payslip_generator import PayslipGenerator
from database.db import init_db, SessionLocal
from database.repository import PayrollRepository

def test_api_and_payslip():
    """Test mock API and payslip generation"""
    
    print("=" * 70)
    print("Testing Mock Likeit API and Payslip Generator")
    print("=" * 70)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    print("   ✓ Database initialized")
    
    # Create API instance
    print("\n2. Creating Mock Likeit API...")
    api = MockLikeitAPI()
    print(f"   ✓ API created with {len(api.MOCK_EMPLOYEES)} employees")
    
    # Fetch payroll data
    print("\n3. Fetching payroll data for August 2025...")
    records = api.get_monthly_payroll(2025, 8)
    print(f"   ✓ Retrieved {len(records)} payroll records")
    
    # Display sample data
    print("\n4. Sample payroll record:")
    sample = records[0]
    print(f"   Employee: {sample.name}")
    print(f"   Period: {sample.pay_period_start} to {sample.pay_period_end}")
    print(f"   Gross Salary: {sample.gross_salary:.2f} €")
    print(f"   Net Payment: {sample.net_payment:.2f} €")
    print(f"   Salary Items: {len(sample.salary_items)}")
    print(f"   Deductions: {len(sample.deductions)}")
    
    # Save to database
    print("\n5. Saving to database...")
    db = SessionLocal()
    repo = PayrollRepository(db)
    
    for record in records:
        # Save employee
        from models.employee import Employee
        employee = Employee(
            employee_id=record.employee_id,
            name=record.name,
            address=record.address,
            bank_details=record.bank_details
        )
        repo.save_employee(employee)
        
        # Save payroll record
        repo.save_payroll_record(record)
        print(f"   ✓ Saved: {record.name}")
    
    db.close()
    
    # Generate payslips
    print("\n6. Generating payslips...")
    generator = PayslipGenerator()
    
    for record in records:
        filepath = generator.generate(record)
        print(f"   ✓ Generated: {Path(filepath).name}")
    
    print("\n" + "=" * 70)
    print("✓ All tests completed successfully!")
    print("=" * 70)
    print(f"\nPayslips saved to: {generator.output_dir}")
    print("\nYou can now open the generated Excel files to verify the output.")

if __name__ == "__main__":
    test_api_and_payslip()