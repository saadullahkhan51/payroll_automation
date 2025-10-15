import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/payroll.db")

# API URLs (mock)
LIKEIT_API_URL = os.getenv("LIKEIT_API_URL", "http://localhost:5001")
TAX_AUTHORITY_API_URL = os.getenv("TAX_AUTHORITY_API_URL", "http://localhost:5002")

# Paths
TEMPLATE_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
(OUTPUT_DIR / "payslips").mkdir(exist_ok=True)
(OUTPUT_DIR / "monthly").mkdir(exist_ok=True)
(OUTPUT_DIR / "annual").mkdir(exist_ok=True)
(OUTPUT_DIR / "tax_forms").mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Application settings
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Swedish Tax Settings
SWEDISH_TAX_RATE = 0.30  # 30% default

# Secret for Flash app, using secrets.token_urlsafe(16)
SECRET_KEY = '69f945eaf34668e31ea598742b4055c4'