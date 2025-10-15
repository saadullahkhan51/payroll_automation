from decimal import Decimal
from datetime import date

def format_currency(amount: Decimal, symbol: str = "€") -> str:
    """Format currency amount"""
    return f"{amount:,.2f} {symbol}"

def format_date_finnish(d: date) -> str:
    """Format date in Finnish style"""
    return d.strftime("%d.%m.%Y")

def format_date_swedish(d: date) -> str:
    """Format date in Swedish style"""
    return d.strftime("%Y-%m-%d")

def format_percentage(rate: Decimal) -> str:
    """Format percentage"""
    return f"{rate:.2f}%"