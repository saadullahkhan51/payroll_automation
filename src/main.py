import logging
from datetime import datetime
from config.settings import LOG_LEVEL
from database.db import init_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for payroll automation"""
    logger.info("Starting Payroll Automation System")
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # TODO: Add orchestration logic
    logger.info("System initialized successfully")
    
    print("=" * 60)
    print("Payroll Automation System v0.1.0")
    print("=" * 60)
    print("\nSystem ready. Next steps:")
    print("1. Implement mock Likeit API")
    print("2. Build payslip generator")
    print("3. Create monthly summary generator")
    print("4. Implement tax form generators")
    print("=" * 60)

if __name__ == "__main__":
    main()