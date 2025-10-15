import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
from decimal import Decimal
from ..models.payroll import PayrollRecord
from config.settings import OUTPUT_DIR

class SKV4788Generator:
    """
    Generate SKV 4788 form - Individual monthly salary and employer contributions
    (Arbetsgivardeklaration - enskild person)
    
    This form reports individual employee salary information monthly to Swedish Tax Authority
    """
    
    def __init__(self):
        self.output_dir = OUTPUT_DIR / "tax_forms"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.SEK_TO_EUR = Decimal('0.086')
    
    def generate(self, payroll_record: PayrollRecord, year: int, month: int) -> str:
        """Generate SKV 4788 form for individual employee"""
        
        # Create root element
        root = ET.Element('Arbetsgivardeklaration')
        root.set('version', '1.0')
        
        # Employer information
        arbetsgivare = ET.SubElement(root, 'Arbetsgivare')
        ET.SubElement(arbetsgivare, 'OrganisationsNummer').text = '556789-0123'
        ET.SubElement(arbetsgivare, 'Namn').text = 'Asiakasyritys Oy'
        
        # Period information
        period = ET.SubElement(root, 'Period')
        ET.SubElement(period, 'År').text = str(year)
        ET.SubElement(period, 'Månad').text = str(month)
        
        # Employee information
        anställd = ET.SubElement(root, 'Anställd')
        ET.SubElement(anställd, 'PersonNummer').text = payroll_record.employee_id
        ET.SubElement(anställd, 'Namn').text = payroll_record.name
        ET.SubElement(anställd, 'Adress').text = payroll_record.address
        
        # Calculate values
        gross_salary_eur = payroll_record.gross_salary
        gross_salary_sek = gross_salary_eur / self.SEK_TO_EUR
        
        tax_free_eur = payroll_record.tax_free_portion
        tax_free_sek = tax_free_eur / self.SEK_TO_EUR
        
        taxable_income_sek = gross_salary_sek - tax_free_sek
        
        # Swedish tax
        swedish_tax_eur = sum(
            abs(d.amount) for d in payroll_record.deductions 
            if 'Swedish' in d.description or 'Ruotsin' in d.description
        )
        swedish_tax_sek = Decimal(str(swedish_tax_eur)) / self.SEK_TO_EUR
        
        # Income information
        inkomst = ET.SubElement(root, 'Inkomst')
        ET.SubElement(inkomst, 'KontantLön').text = f"{float(taxable_income_sek):.2f}"
        ET.SubElement(inkomst, 'Förmåner').text = f"{float(tax_free_sek):.2f}"
        ET.SubElement(inkomst, 'TotalInkomst').text = f"{float(gross_salary_sek):.2f}"
        
        # Tax deductions
        skatt = ET.SubElement(root, 'Skatt')
        ET.SubElement(skatt, 'PreliminarSkatt').text = f"{float(swedish_tax_sek):.2f}"
        ET.SubElement(skatt, 'SkatteSats').text = "30"
        
        # Employer contributions
        avgifter = ET.SubElement(root, 'Arbetsgivaravgifter')
        employer_contribution_rate = Decimal('0.3142')
        employer_contributions = taxable_income_sek * employer_contribution_rate
        
        ET.SubElement(avgifter, 'Pensionsavgift').text = f"{float(employer_contributions * Decimal('0.1042')):.2f}"
        ET.SubElement(avgifter, 'Sjukförsäkring').text = f"{float(employer_contributions * Decimal('0.0368')):.2f}"
        ET.SubElement(avgifter, 'Arbetsskada').text = f"{float(employer_contributions * Decimal('0.0068')):.2f}"
        ET.SubElement(avgifter, 'Övrigt').text = f"{float(employer_contributions * Decimal('0.1664')):.2f}"
        ET.SubElement(avgifter, 'TotalAvgifter').text = f"{float(employer_contributions):.2f}"
        
        # Working hours
        arbetstid = ET.SubElement(root, 'Arbetstid')
        total_hours = sum(
            item.quantity for item in payroll_record.salary_items 
            if item.quantity and item.code.startswith('121')
        )
        ET.SubElement(arbetstid, 'AntalTimmar').text = f"{float(total_hours):.2f}"
        
        # Additional information
        tillagg = ET.SubElement(root, 'Tilläggsinformation')
        ET.SubElement(tillagg, 'Kommentar').text = 'Construction worker - Cross-border employment'
        
        # Convert to formatted XML string
        xml_str = self._prettify_xml(root)
        
        # Generate filename - sanitize employee_id
        safe_employee_id = payroll_record.employee_id.replace('/', '-').replace('\\', '-')
        filename = f"SKV4788_{safe_employee_id}_{year}_{month:02d}.xml"
        filepath = self.output_dir / filename
        
        # Save XML file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(xml_str)
        
        return str(filepath)
    
    def _prettify_xml(self, elem):
        """Return a pretty-printed XML string"""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")