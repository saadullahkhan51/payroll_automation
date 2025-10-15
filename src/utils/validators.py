import re
from decimal import Decimal

def validate_swedish_personal_number(personal_number: str) -> bool:
    """Validate Swedish personal number format"""
    pattern = r'^\d{8}-\d{4}$'
    return bool(re.match(pattern, personal_number))

def validate_iban(iban: str) -> bool:
    """Basic IBAN validation"""
    iban = iban.replace(' ', '')
    return len(iban) >= 15 and iban[:2].isalpha()

def validate_tax_rate(rate: Decimal) -> bool:
    """Validate tax rate is within reasonable bounds"""
    return Decimal('0') <= rate <= Decimal('100')