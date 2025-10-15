from dataclasses import dataclass
from typing import Optional

@dataclass
class Employee:
    """Employee data model"""
    employee_id: str
    name: str
    address: str
    bank_details: str
    
    def __str__(self):
        return f"Employee({self.employee_id}, {self.name})"