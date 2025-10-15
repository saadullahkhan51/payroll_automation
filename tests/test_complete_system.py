import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from api.mock_likeit import MockLikeitAPI
from processors.payslip_generator import PayslipGenerator
from processors.personal_tax_calculator import PersonalTaxCalculator
from processors.annual_summary_generator import AnnualSummaryGenerator
from processors.monthly_all_workers_generator import MonthlyAllWorkersGenerator
from database.db import init_db, SessionLocal
from database.repository import PayrollRepository
from models.employee import Employee

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_success(message):
    """Print success message"""
    print(f"  ✓ {message}")

def print_info(message):
    """Print info message"""
    print(f"  → {message}")

def print_error(message):
    """Print error message"""
    print(f"  ✗ {message}")

def test_complete_system():
    """Test the complete payroll automation system"""
    
    start_time = datetime.now()
    
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "PAYROLL AUTOMATION SYSTEM - FULL TEST" + " " * 21 + "║")
    print("╚" + "═" * 78 + "╝")
    
    # Configuration
    year = 2025
    test_month = 8  # August for single month tests
    
    # Statistics tracking
    stats = {
        'employees': 0,
        'months_generated': 0,
        'payslips': 0,
        'monthly_summaries': 0,
        'personal_tax_calcs': 0,
        'annual_summaries': 0,
        'errors': []
    }
    
    try:
        # ====================================================================
        # STEP 1: Initialize Database
        # ====================================================================
        print_section("STEP 1: Database Initialization")
        init_db()
        db = SessionLocal()
        repo = PayrollRepository(db)
        print_success("Database initialized successfully")
        
        # ====================================================================
        # STEP 2: Initialize Mock API
        # ====================================================================
        print_section("STEP 2: Mock Likeit API Setup")
        api = MockLikeitAPI()
        employees = api.get_all_employees()
        stats['employees'] = len(employees)
        print_success(f"Mock API initialized with {len(employees)} employees")
        for emp in employees:
            print_info(f"Employee: {emp['name']} ({emp['employee_id']})")
        
        # ====================================================================
        # STEP 3: Generate Full Year Payroll Data
        # ====================================================================
        print_section("STEP 3: Generating Full Year Payroll Data")
        print_info(f"Generating data for all 12 months of {year}...")
        
        all_months_data = []
        
        for month in range(1, 13):
            print(f"\n  Processing Month {month:02d}/{year}...")
            
            try:
                # Get payroll data from API
                records = api.get_monthly_payroll(year, month)
                all_months_data.append((month, records))
                
                # Save to database
                for record in records:
                    # Save employee
                    employee = Employee(
                        employee_id=record.employee_id,
                        name=record.name,
                        address=record.address,
                        bank_details=record.bank_details
                    )
                    repo.save_employee(employee)
                    
                    # Save payroll record
                    repo.save_payroll_record(record)
                
                stats['months_generated'] += 1
                print_success(f"Month {month:02d}: {len(records)} records processed and saved")
                
            except Exception as e:
                error_msg = f"Month {month:02d}: {str(e)}"
                stats['errors'].append(error_msg)
                print_error(error_msg)
        
        # ====================================================================
        # STEP 4: Generate Individual Payslips (August only)
        # ====================================================================
        print_section(f"STEP 4: Generating Individual Payslips (August {year})")
        payslip_generator = PayslipGenerator()
        
        august_records = api.get_monthly_payroll(year, test_month)
        
        for record in august_records:
            try:
                filepath = payslip_generator.generate(record)
                stats['payslips'] += 1
                print_success(f"Payslip: {record.name} → {Path(filepath).name}")
            except Exception as e:
                error_msg = f"Payslip for {record.name}: {str(e)}"
                stats['errors'].append(error_msg)
                print_error(error_msg)
        
        print_info(f"Payslips saved to: {payslip_generator.output_dir}")
        
        
        # ====================================================================
        # STEP 6: Generate Personal Annual Tax Calculations
        # ====================================================================
        print_section(f"STEP 6: Generating Personal Annual Tax Calculations")
        personal_tax_calc = PersonalTaxCalculator(repo)
        
        for emp in employees:
            try:
                filepath = personal_tax_calc.generate_personal_annual_summary(
                    emp['employee_id'], 
                    year
                )
                stats['personal_tax_calcs'] += 1
                print_success(f"Personal tax calc: {emp['name']} → {Path(filepath).name}")
            except Exception as e:
                error_msg = f"Personal tax calc for {emp['name']}: {str(e)}"
                stats['errors'].append(error_msg)
                print_error(error_msg)
        
        print_info(f"Personal tax calculations saved to: {personal_tax_calc.output_dir}")
        
        # ====================================================================
        # STEP 7: Generate Annual Summary (All Workers)
        # ====================================================================
        print_section(f"STEP 7: Generating Annual Summary for All Workers")
        annual_summary_gen = AnnualSummaryGenerator(repo)
        
        try:
            filepath = annual_summary_gen.generate_all_workers_annual_summary(year)
            stats['annual_summaries'] += 1
            print_success(f"Annual summary (all workers) → {Path(filepath).name}")
            print_info(f"File saved to: {filepath}")
        except Exception as e:
            error_msg = f"Annual summary (all workers): {str(e)}"
            stats['errors'].append(error_msg)
            print_error(error_msg)
        
        # ====================================================================
        # STEP 8: Generate Annual Monthly Details
        # ====================================================================
        print_section(f"STEP 8: Generating All Workers Monthly Details")
        annual_monthly_gen = MonthlyAllWorkersGenerator(repo)
        
        try:
            filepath = annual_monthly_gen.generate(year)
            stats['annual_summaries'] += 1
            print_success(f"Annual monthly details → {Path(filepath).name}")
            print_info(f"File saved to: {filepath}")
        except Exception as e:
            error_msg = f"Annual monthly details: {str(e)}"
            stats['errors'].append(error_msg)
            print_error(error_msg)
        
        # ====================================================================
        # Database Cleanup
        # ====================================================================
        db.close()
        
    except Exception as e:
        print_error(f"Critical error: {str(e)}")
        stats['errors'].append(f"Critical: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # ====================================================================
    # FINAL REPORT
    # ====================================================================
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print_section("TEST SUMMARY")
    
    print(f"\n  Execution Time: {duration:.2f} seconds")
    print(f"\n  📊 Statistics:")
    print(f"     • Employees Processed: {stats['employees']}")
    print(f"     • Months Generated: {stats['months_generated']}/12")
    print(f"     • Total Payroll Records: {stats['employees'] * stats['months_generated']}")
    print(f"     • Individual Payslips: {stats['payslips']}")
    print(f"     • Monthly Summaries: {stats['monthly_summaries']}")
    print(f"     • Personal Tax Calculations: {stats['personal_tax_calcs']}")
    print(f"     • Annual Summaries: {stats['annual_summaries']}")
    
    print(f"\n  📁 Output Directories:")
    print(f"     • Payslips: output/payslips/")
    print(f"     • Monthly Summaries: output/monthly/")
    print(f"     • Annual Reports: output/annual/")
    
    if stats['errors']:
        print(f"\n  ⚠️  Errors Encountered: {len(stats['errors'])}")
        for error in stats['errors']:
            print(f"     • {error}")
    else:
        print(f"\n  ✅ No errors encountered!")
    
    print("\n" + "╔" + "═" * 78 + "╗")
    if not stats['errors']:
        print("║" + " " * 25 + "🎉 ALL TESTS PASSED! 🎉" + " " * 26 + "║")
    else:
        print("║" + " " * 20 + "⚠️  TESTS COMPLETED WITH ERRORS ⚠️" + " " * 20 + "║")
    print("╚" + "═" * 78 + "╝\n")
    
    # File listing
    print_section("GENERATED FILES")
    
    from config.settings import OUTPUT_DIR
    
    print("\n  Individual Payslips (output/payslips/):")
    payslip_dir = OUTPUT_DIR / "payslips"
    if payslip_dir.exists():
        files = sorted(payslip_dir.glob("*.xlsx"))
        for f in files[:5]:  # Show first 5
            print(f"     • {f.name}")
        if len(files) > 5:
            print(f"     • ... and {len(files) - 5} more files")
    
    print("\n  Monthly Summaries (output/monthly/):")
    monthly_dir = OUTPUT_DIR / "monthly"
    if monthly_dir.exists():
        files = sorted(monthly_dir.glob("*.xlsx"))
        for f in files:
            print(f"     • {f.name}")
    
    print("\n  Annual Reports (output/annual/):")
    annual_dir = OUTPUT_DIR / "annual"
    if annual_dir.exists():
        files = sorted(annual_dir.glob("*.xlsx"))
        for f in files:
            print(f"     • {f.name}")
    
    print("\n" + "═" * 80)
    print("  Next Steps:")
    print("  1. Open the generated Excel files to verify formatting")
    print("  2. Check the personal tax calculations match expected format")
    print("  3. Review the annual summaries for accuracy")
    print("  4. Proceed to build SKV tax form generators (4788 & 4786)")
    print("═" * 80 + "\n")

if __name__ == "__main__":
    test_complete_system()