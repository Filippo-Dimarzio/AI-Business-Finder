"""
Database migration script to add Google Places fields.
"""

import os
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Float, String, JSON, text
from dotenv import load_dotenv

load_dotenv()

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
    
    # Add new columns if they don't exist
    new_columns = [
        Column('google_photos_count', Integer),
        Column('google_review_count', Integer),
        Column('google_rating', Float),
        Column('google_place_id', String(255)),
        Column('google_business_status', String(50)),
        Column('google_types', JSON)
    ]
    
    # Add columns one by one
    with engine.connect() as conn:
        for column in new_columns:
            if column.name not in businesses.columns:
                conn.execute(text(f'ALTER TABLE businesses ADD COLUMN {column.name} {column.type}'))
                print(f"Added column: {column.name}")
        
        conn.commit()

if __name__ == "__main__":
    migrate_database()
    print("Migration completed successfully")