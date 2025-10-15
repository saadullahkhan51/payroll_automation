import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
from typing import List
from decimal import Decimal
from datetime import date
from ..models.payroll import PayrollRecord
from config.settings import OUTPUT_DIR

class SKV4786Generator:
    """
    Generate SKV 4786 form - Combined monthly employer declaration
    (Arbetsgivardeklaration - sammanställning)
    
    This form reports the total monthly salary information for all employees
    """
    
    def __init__(self):
        self.output_dir = OUTPUT_DIR / "tax_forms"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.SEK_TO_EUR = Decimal('0.086')
    
    def generate(self, payroll_records: List[PayrollRecord], year: int, month: int) -> str:
        """Generate SKV 4786 form for all employees combined"""
        
        # Create root element
        root = ET.Element('Arbetsgivardeklaration')
        root.set('version', '1.0')
        root.set('typ', 'Sammanställning')
        
        # Employer information
        arbetsgivare = ET.SubElement(root, 'Arbetsgivare')
        ET.SubElement(arbetsgivare, 'OrganisationsNummer').text = '556789-0123'
        ET.SubElement(arbetsgivare, 'Namn').text = 'Asiakasyritys Oy'
        ET.SubElement(arbetsgivare, 'Adress').text = 'Meritullentie 12, 02110 Espoo, Finland'
        ET.SubElement(arbetsgivare, 'KontaktPerson').text = 'HR Manager'
        ET.SubElement(arbetsgivare, 'Telefon').text = '+358 40 123 4567'
        ET.SubElement(arbetsgivare, 'Email').text = 'hr@asiakasyritys.fi'
        
        # Period information
        period = ET.SubElement(root, 'Period')
        ET.SubElement(period, 'År').text = str(year)
        ET.SubElement(period, 'Månad').text = str(month)
        ET.SubElement(period, 'AntalAnställda').text = str(len(set(r.employee_id for r in payroll_records)))
        
        # Calculate totals
        totals = self._calculate_totals(payroll_records)
        
        # Summary information
        sammanfattning = ET.SubElement(root, 'Sammanfattning')
        
        # Total salaries
        löner = ET.SubElement(sammanfattning, 'Löner')
        ET.SubElement(löner, 'TotalKontantLön').text = f"{float(totals['taxable_income_sek']):.2f}"
        ET.SubElement(löner, 'TotalFörmåner').text = f"{float(totals['tax_free_sek']):.2f}"
        ET.SubElement(löner, 'TotalBruttoLön').text = f"{float(totals['gross_salary_sek']):.2f}"
        
        # Total taxes
        skatter = ET.SubElement(sammanfattning, 'Skatter')
        ET.SubElement(skatter, 'TotalPreliminarSkatt').text = f"{float(totals['swedish_tax_sek']):.2f}"
        ET.SubElement(skatter, 'GenomsnittligSkatteSats').text = "30.00"
        
        # Total employer contributions
        avgifter = ET.SubElement(sammanfattning, 'Arbetsgivaravgifter')
        employer_contribution_rate = Decimal('0.3142')
        total_employer_contributions = totals['taxable_income_sek'] * employer_contribution_rate
        
        ET.SubElement(avgifter, 'TotalPensionsavgift').text = f"{float(total_employer_contributions * Decimal('0.1042')):.2f}"
        ET.SubElement(avgifter, 'TotalSjukförsäkring').text = f"{float(total_employer_contributions * Decimal('0.0368')):.2f}"
        ET.SubElement(avgifter, 'TotalArbetsskada').text = f"{float(total_employer_contributions * Decimal('0.0068')):.2f}"
        ET.SubElement(avgifter, 'TotalÖvrigt').text = f"{float(total_employer_contributions * Decimal('0.1664')):.2f}"
        ET.SubElement(avgifter, 'TotalArbetsgivaravgifter').text = f"{float(total_employer_contributions):.2f}"
        
        # Total amount to pay
        betalning = ET.SubElement(root, 'Betalning')
        total_to_pay = totals['swedish_tax_sek'] + total_employer_contributions
        ET.SubElement(betalning, 'TotalAttBetala').text = f"{float(total_to_pay):.2f}"
        ET.SubElement(betalning, 'Förfallodatum').text = self._get_due_date(year, month)
        ET.SubElement(betalning, 'OCRNummer').text = self._generate_ocr_number(year, month)
        
        # Individual employee list
        anställda = ET.SubElement(root, 'AnställdaLista')
        
        # Get unique employees
        unique_employees = {}
        for record in payroll_records:
            if record.employee_id not in unique_employees:
                unique_employees[record.employee_id] = []
            unique_employees[record.employee_id].append(record)
        
        for employee_id, records in unique_employees.items():
            person = ET.SubElement(anställda, 'Person')
            ET.SubElement(person, 'PersonNummer').text = employee_id
            ET.SubElement(person, 'Namn').text = records[0].name
            
            # Sum for this employee
            emp_gross = sum(r.gross_salary for r in records)
            emp_gross_sek = emp_gross / self.SEK_TO_EUR
            
            emp_tax = sum(
                sum(abs(d.amount) for d in r.deductions 
                    if 'Swedish' in d.description or 'Ruotsin' in d.description)
                for r in records
            )
            emp_tax_sek = Decimal(str(emp_tax)) / self.SEK_TO_EUR
            
            ET.SubElement(person, 'BruttoLön').text = f"{float(emp_gross_sek):.2f}"
            ET.SubElement(person, 'PreliminarSkatt').text = f"{float(emp_tax_sek):.2f}"
        
        # Signature section
        underskrift = ET.SubElement(root, 'Underskrift')
        ET.SubElement(underskrift, 'Datum').text = date.today().isoformat()
        ET.SubElement(underskrift, 'Undertecknare').text = 'System Generated'
        
        # Convert to formatted XML string
        xml_str = self._prettify_xml(root)
        
        # Generate filename
        filename = f"SKV4786_Combined_{year}_{month:02d}.xml"
        filepath = self.output_dir / filename
        
        # Save XML file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(xml_str)
        
        return str(filepath)
    
    def _calculate_totals(self, payroll_records: List[PayrollRecord]) -> dict:
        """Calculate totals from all payroll records"""
        totals = {
            'gross_salary_sek': Decimal('0'),
            'taxable_income_sek': Decimal('0'),
            'tax_free_sek': Decimal('0'),
            'swedish_tax_sek': Decimal('0')
        }
        
        for record in payroll_records:
            gross_sek = record.gross_salary / self.SEK_TO_EUR
            tax_free_sek = record.tax_free_portion / self.SEK_TO_EUR
            taxable_sek = gross_sek - tax_free_sek
            
            swedish_tax_eur = sum(
                abs(d.amount) for d in record.deductions 
                if 'Swedish' in d.description or 'Ruotsin' in d.description
            )
            swedish_tax_sek = Decimal(str(swedish_tax_eur)) / self.SEK_TO_EUR
            
            totals['gross_salary_sek'] += gross_sek
            totals['taxable_income_sek'] += taxable_sek
            totals['tax_free_sek'] += tax_free_sek
            totals['swedish_tax_sek'] += swedish_tax_sek
        
        return totals
    
    def _get_due_date(self, year: int, month: int) -> str:
        """Get payment due date (12th of following month)"""
        if month == 12:
            return f"{year + 1}-01-12"
        else:
            return f"{year}-{month + 1:02d}-12"
    
    def _generate_ocr_number(self, year: int, month: int) -> str:
        """Generate OCR reference number for payment"""
        base = f"{year}{month:02d}556789"
        
        def luhn_checksum(card_number):
            def digits_of(n):
                return [int(d) for d in str(n)]
            digits = digits_of(card_number)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d * 2))
            return checksum % 10
        
        check = luhn_checksum(base)
        return f"{base}{check}"
    
    def _prettify_xml(self, elem):
        """Return a pretty-printed XML string"""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")