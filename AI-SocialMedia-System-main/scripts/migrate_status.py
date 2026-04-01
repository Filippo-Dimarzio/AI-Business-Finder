"""
Migrate database to add status column
"""
from database import init_database, get_db_session, Business, BusinessStatus
from loguru import logger

def migrate_status():
    """Add status column and set default values"""
    try:
        # Reinitialize database with new schema
        init_database()
        
        # Get session
        session = get_db_session()
        
        # Update existing records to have a default status
        businesses = session.query(Business).all()
        for business in businesses:
            if not hasattr(business, 'status'):
                business.status = BusinessStatus.PENDING
        
        session.commit()
        logger.info("Successfully migrated database to include status column")
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate_status()