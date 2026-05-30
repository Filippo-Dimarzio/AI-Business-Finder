"""
Database migration script to add Google Places fields.
"""

import os
import re
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Float, String, JSON, text
from dotenv import load_dotenv

load_dotenv()

# Allowed column names and their SQL types for migration safety
_ALLOWED_COLUMNS = {
    'google_photos_count': 'INTEGER',
    'google_review_count': 'INTEGER',
    'google_rating': 'FLOAT',
    'google_place_id': 'VARCHAR(255)',
    'google_business_status': 'VARCHAR(50)',
    'google_types': 'JSON',
}

_VALID_IDENTIFIER = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

def migrate_database():
    """Add new Google Places columns to the businesses table"""
    from database import get_database_url
    
    # Create engine
    engine = create_engine(get_database_url())
    
    # Get metadata
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    # Get businesses table
    businesses = Table('businesses', metadata)
    
    # Add columns one by one using the allow-list
    with engine.connect() as conn:
        for col_name, col_type in _ALLOWED_COLUMNS.items():
            if not _VALID_IDENTIFIER.match(col_name):
                raise ValueError(f"Invalid column name: {col_name}")
            if col_name not in businesses.columns:
                stmt = text(f'ALTER TABLE businesses ADD COLUMN {col_name} {col_type}')
                conn.execute(stmt)
                print(f"Added column: {col_name}")
        
        conn.commit()

if __name__ == "__main__":
    migrate_database()
    print("Migration completed successfully")