from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from pathlib import Path
import sys, os
from datetime import datetime, date
import json

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from api.mock_likeit import MockLikeitAPI
from processors.payslip_generator import PayslipGenerator
from processors.monthly_all_workers_generator import MonthlyAllWorkersGenerator
from processors.personal_tax_calculator import PersonalTaxCalculator
from processors.annual_summary_generator import AnnualSummaryGenerator
from database.db import init_db, SessionLocal
from database.repository import PayrollRepository
from models.employee import Employee
from config.settings import OUTPUT_DIR, SECRET_KEY, DATA_DIR

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = os.getenv('DEBUG', 'False').lower() == 'true'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

for directory in ['payslips', 'monthly', 'annual', 'tax_forms']:
    (OUTPUT_DIR / directory).mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


init_db()

def get_generation_history():
    """Get list of all generated files with metadata"""
    history = []
    
    for directory in [OUTPUT_DIR / 'payslips', OUTPUT_DIR / 'monthly', OUTPUT_DIR / 'annual', OUTPUT_DIR / 'tax_forms']:
        if directory.exists():
            for file in directory.glob('*.xlsx'):
                stat = file.stat()
                history.append({
                    'filename': file.name,
                    'path': str(file),
                    'size': f"{stat.st_size / 1024:.2f} KB",
                    'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                    'type': directory.name
                })
    
    history.sort(key=lambda x: x['created'], reverse=True)
    return history

def generate_payroll_data(year, month):
    """Generate payroll data for a given month"""
    api = MockLikeitAPI()
    
    all_records = []
    employees = api.get_all_employees()
    
    # First period (1-15)
    for emp in employees:
        record = api.get_employee_payroll(emp['employee_id'], year, month)
        record.pay_period_start = date(year, month, 1)
        record.pay_period_end = date(year, month, 15)
        all_records.append(record)
    
    # Second period (16-31)
    for emp in employees:
        record = api.get_employee_payroll(emp['employee_id'], year, month)
        if month == 12:
            last_day = 31
        elif month in [4, 6, 9, 11]:
            last_day = 30
        elif month == 2:
            last_day = 28 if year % 4 != 0 else 29
        else:
            last_day = 31
        
        record.pay_period_start = date(year, month, 16)
        record.pay_period_end = date(year, month, last_day)
        all_records.append(record)
    
    # Save to database
    db = SessionLocal()
    repo = PayrollRepository(db)
    
    for record in all_records:
        employee = Employee(
            employee_id=record.employee_id,
            name=record.name,
            address=record.address,
            bank_details=record.bank_details
        )
        repo.save_employee(employee)
        repo.save_payroll_record(record)
    
    db.close()
    return all_records

# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/generate')
def generate_page():
    """Report generation page"""
    return render_template('generate.html')

@app.route('/history')
def history_page():
    """File history page"""
    files = get_generation_history()
    return render_template('history.html', files=files)

# ============================================================================
# API Endpoints
# ============================================================================

@app.route('/api/employees')
def get_employees():
    """Get list of employees"""
    api = MockLikeitAPI()
    employees = api.get_all_employees()
    return jsonify(employees)

@app.route('/api/generate/payslips', methods=['POST'])
def generate_payslips():
    """Generate individual payslips"""
    data = request.json
    year = int(data.get('year'))
    month = int(data.get('month'))
    
    try:
        # Generate data
        records = generate_payroll_data(year, month)
        
        # Generate payslips for first period only (or filter as needed)
        first_period = [r for r in records if r.pay_period_start.day == 1]
        
        generator = PayslipGenerator()
        generated_files = []
        
        for record in first_period:
            filepath = generator.generate(record)
            generated_files.append(Path(filepath).name)
        
        return jsonify({
            'success': True,
            'message': f'Generated {len(generated_files)} payslips',
            'files': generated_files
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/generate/monthly-all-workers', methods=['POST'])
def generate_monthly_all_workers():
    """Generate monthly all workers report"""
    data = request.json
    year = int(data.get('year'))
    month = int(data.get('month'))
    
    try:
        # Generate data
        records = generate_payroll_data(year, month)
        
        # Generate monthly all workers
        generator = MonthlyAllWorkersGenerator()
        filepath = generator.generate(records, year, month)
        
        return jsonify({
            'success': True,
            'message': 'Monthly all workers report generated successfully',
            'file': Path(filepath).name
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/generate/personal-tax', methods=['POST'])
def generate_personal_tax():
    """Generate personal tax calculations"""
    data = request.json
    year = int(data.get('year'))
    employee_id = data.get('employee_id')
    
    try:
        # Generate data for full year if needed
        for month in range(1, 13):
            generate_payroll_data(year, month)
        
        # Generate personal tax calculation
        db = SessionLocal()
        repo = PayrollRepository(db)
        calculator = PersonalTaxCalculator(repo)
        
        if employee_id == 'all':
            api = MockLikeitAPI()
            employees = api.get_all_employees()
            generated_files = []
            
            for emp in employees:
                filepath = calculator.generate_personal_annual_summary(emp['employee_id'], year)
                generated_files.append(Path(filepath).name)
            
            db.close()
            return jsonify({
                'success': True,
                'message': f'Generated {len(generated_files)} personal tax calculations',
                'files': generated_files
            })
        else:
            filepath = calculator.generate_personal_annual_summary(employee_id, year)
            db.close()
            
            return jsonify({
                'success': True,
                'message': 'Personal tax calculation generated successfully',
                'file': Path(filepath).name
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/generate/annual-summary', methods=['POST'])
def generate_annual_summary():
    """Generate annual summary for all workers"""
    data = request.json
    year = int(data.get('year'))
    
    try:
        # Generate data for full year
        for month in range(1, 13):
            generate_payroll_data(year, month)
        
        # Generate annual summary
        db = SessionLocal()
        repo = PayrollRepository(db)
        generator = AnnualSummaryGenerator(repo)
        
        filepath = generator.generate_all_workers_annual_summary(year)
        db.close()
        
        return jsonify({
            'success': True,
            'message': 'Annual summary generated successfully',
            'file': Path(filepath).name
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/generate/all', methods=['POST'])
def generate_all_reports():
    """Generate all reports for a given period"""
    data = request.json
    year = int(data.get('year'))
    month = int(data.get('month', 1))
    
    try:
        generated = {
            'payslips': [],
            'monthly': [],
            'annual': []
        }
        
        # Generate monthly data
        records = generate_payroll_data(year, month)
        
        # Payslips
        first_period = [r for r in records if r.pay_period_start.day == 1]
        payslip_gen = PayslipGenerator()
        for record in first_period:
            filepath = payslip_gen.generate(record)
            generated['payslips'].append(Path(filepath).name)
        
        monthly_workers_gen = MonthlyAllWorkersGenerator()
        filepath = monthly_workers_gen.generate(records, year, month)
        generated['monthly'].append(Path(filepath).name)
        
        return jsonify({
            'success': True,
            'message': 'All reports generated successfully',
            'generated': generated
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/download/<path:filename>')
def download_file(filename):
    """Download a generated file"""
    # Search in all output directories
    for directory in [OUTPUT_DIR / 'payslips', OUTPUT_DIR / 'monthly', OUTPUT_DIR / 'annual', OUTPUT_DIR / 'tax_forms']:
        filepath = directory / filename
        if filepath.exists():
            return send_file(filepath, as_attachment=True)
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/delete/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete a generated file"""
    for directory in [OUTPUT_DIR / 'payslips', OUTPUT_DIR / 'monthly', OUTPUT_DIR / 'annual']:
        filepath = directory / filename
        if filepath.exists():
            filepath.unlink()
            return jsonify({'success': True, 'message': 'File deleted'})
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/submit-tax')
def submit_tax_page():
    """Swedish Tax Authority submission page"""
    return render_template('submit_tax.html')

@app.route('/api/generate/skv4788', methods=['POST'])
def generate_skv4788():
    """Generate SKV 4788 forms (individual employees)"""
    data = request.json
    year = int(data.get('year'))
    month = int(data.get('month'))
    
    try:
        # Generate data
        records = generate_payroll_data(year, month)
        
        # Generate SKV 4788 forms
        from processors.skv4788_generator import SKV4788Generator
        generator = SKV4788Generator()
        generated_files = []
        
        # Filter to first period only (or process as needed)
        first_period = [r for r in records if r.pay_period_start.day == 1]
        
        for record in first_period:
            filepath = generator.generate(record, year, month)
            generated_files.append(Path(filepath).name)
        
        return jsonify({
            'success': True,
            'message': f'Generated {len(generated_files)} SKV 4788 forms',
            'files': generated_files
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/generate/skv4786', methods=['POST'])
def generate_skv4786():
    """Generate SKV 4786 form (combined)"""
    data = request.json
    year = int(data.get('year'))
    month = int(data.get('month'))
    
    try:
        # Generate data
        records = generate_payroll_data(year, month)
        
        # Generate SKV 4786 form
        from processors.skv4786_generator import SKV4786Generator
        generator = SKV4786Generator()
        filepath = generator.generate(records, year, month)
        
        return jsonify({
            'success': True,
            'message': 'SKV 4786 form generated successfully',
            'file': Path(filepath).name
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/submit/skv4788', methods=['POST'])
def submit_skv4788():
    """Mock submission of SKV 4788 forms to Swedish Tax Authority"""
    data = request.json
    files = data.get('files', [])
    
    # Simulate processing time
    import time
    time.sleep(2)
    
    # Mock successful submission
    db = SessionLocal()
    repo = PayrollRepository(db)
    
    submitted = []
    for filename in files:
        # Extract info from filename
        parts = filename.replace('.xml', '').split('_')
        employee_id = parts[1]
        year = int(parts[2])
        month = int(parts[3])
        
        # Save submission record
        submission = repo.save_tax_form_submission(
            form_type='SKV4788',
            year=year,
            month=month,
            employee_id=employee_id,
            file_path=str(OUTPUT_DIR / 'tax_forms' / filename)
        )
        
        # Mock successful response
        repo.update_submission_status(
            submission.id,
            status='submitted',
            reference_number=f'SKV{year}{month:02d}{employee_id[:4]}{submission.id:04d}',
            response_data={
                'status': 'accepted',
                'message': 'Form successfully submitted to Skatteverket',
                'timestamp': datetime.now().isoformat()
            }
        )
        
        submitted.append({
            'file': filename,
            'reference': f'SKV{year}{month:02d}{employee_id[:4]}{submission.id:04d}',
            'status': 'submitted'
        })
    
    db.close()
    
    return jsonify({
        'success': True,
        'message': f'Successfully submitted {len(submitted)} forms to Skatteverket',
        'submitted': submitted
    })

@app.route('/api/submit/skv4786', methods=['POST'])
def submit_skv4786():
    """Mock submission of SKV 4786 form to Swedish Tax Authority"""
    data = request.json
    filename = data.get('file')
    
    # Simulate processing time
    import time
    time.sleep(2)
    
    # Extract info from filename
    parts = filename.replace('.xml', '').split('_')
    year = int(parts[2])
    month = int(parts[3])
    
    # Mock successful submission
    db = SessionLocal()
    repo = PayrollRepository(db)
    
    submission = repo.save_tax_form_submission(
        form_type='SKV4786',
        year=year,
        month=month,
        employee_id=None,
        file_path=str(OUTPUT_DIR / 'tax_forms' / filename)
    )
    
    reference_number = f'SKV4786-{year}{month:02d}-{submission.id:06d}'
    
    repo.update_submission_status(
        submission.id,
        status='submitted',
        reference_number=reference_number,
        response_data={
            'status': 'accepted',
            'message': 'Combined declaration successfully submitted to Skatteverket',
            'amount_due': '125000.00 SEK',
            'payment_due_date': f'{year}-{month+1:02d}-12',
            'ocr_reference': f'{year}{month:02d}556789{submission.id}',
            'timestamp': datetime.now().isoformat()
        }
    )
    
    db.close()
    
    return jsonify({
        'success': True,
        'message': 'Combined declaration successfully submitted to Skatteverket',
        'reference': reference_number,
        'payment_info': {
            'amount': '125000.00 SEK',
            'due_date': f'{year}-{month+1:02d}-12',
            'ocr': f'{year}{month:02d}556789{submission.id}'
        }
    })

@app.route('/api/submissions')
def get_submissions():
    """Get all tax form submissions"""
    db = SessionLocal()
    repo = PayrollRepository(db)
    
    from database.models import TaxFormSubmissionDB
    submissions = db.query(TaxFormSubmissionDB).order_by(
        TaxFormSubmissionDB.submission_date.desc()
    ).all()
    
    result = []
    for sub in submissions:
        result.append({
            'id': sub.id,
            'form_type': sub.form_type,
            'year': sub.year,
            'month': sub.month,
            'employee_id': sub.employee_id,
            'status': sub.status,
            'reference': sub.reference_number,
            'submitted_at': sub.submission_date.strftime('%Y-%m-%d %H:%M:%S') if sub.submission_date else None,
            'file': Path(sub.form_file_path).name if sub.form_file_path else None
        })
    
    db.close()
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])