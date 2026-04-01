"""
Database configuration and models for the Business Finder system.
"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, Text, JSON, text, Enum
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from datetime import datetime
import enum
import os
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

Base = declarative_base()

class BusinessStatus(enum.Enum):
    """Enum for business approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class Business(Base):
    """Main business entity table"""
    __tablename__ = "businesses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    address = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True)
    city = Column(String(100), nullable=True, index=True)
    postcode = Column(String(20), nullable=True, index=True)
    
    # Normalized fields
    normalized_name = Column(String(255), nullable=True, index=True)
    normalized_address = Column(Text, nullable=True)
    
    # Digital presence detection
    website_present = Column(Boolean, default=False, index=True)
    website_url = Column(String(500), nullable=True)
    social_present = Column(Boolean, default=False, index=True)
    social_links = Column(JSON, nullable=True)  # Store as JSON array
    google_maps_photos = Column(Boolean, default=False, index=True)
    delivery_platforms = Column(JSON, nullable=True)  # Store delivery platform links
    blog_mentions = Column(JSON, nullable=True)  # Store blog/review site mentions
    online_ordering = Column(Boolean, default=False, index=True)
    digital_presence_details = Column(JSON, nullable=True)  # Store detailed findings
    
    # Google Places specific data
    google_photos_count = Column(Integer, default=0)
    google_review_count = Column(Integer, default=0)
    google_rating = Column(Float, nullable=True)
    google_place_id = Column(String(255), nullable=True)
    google_business_status = Column(String(50), nullable=True)
    google_types = Column(JSON, nullable=True)
    
    # Classification results
    no_website_no_social = Column(Boolean, default=False, index=True)
    confidence_score = Column(Float, nullable=True, index=True)
    status = Column(Enum(BusinessStatus), default=BusinessStatus.PENDING, nullable=False)
    
    # Metadata
    sources = Column(JSON, nullable=True)  # List of data sources
    last_checked_date = Column(DateTime, default=datetime.utcnow)
    human_review = Column(String(20), nullable=True)  # 'approved', 'rejected', 'pending'
    human_reviewer = Column(String(100), nullable=True)
    human_review_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DataSource(Base):
    """Track data sources and their reliability"""
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    source_type = Column(String(50), nullable=False)  # 'api', 'csv', 'osm', 'manual'
    reliability_score = Column(Float, default=0.5)  # 0-1 scale
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    config = Column(JSON, nullable=True)  # Store API keys, endpoints, etc.

class ProcessingLog(Base):
    """Log processing activities and errors"""
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, nullable=True)
    process_type = Column(String(50), nullable=False)  # 'ingest', 'normalize', 'website_check', etc.
    status = Column(String(20), nullable=False)  # 'success', 'error', 'warning'
    message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

def get_database_url():
    """Get database URL from environment variables"""
    url = os.getenv("DATABASE_URL", "sqlite:///./business_finder.db")
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return url

def init_database():
    """Initialize database tables"""
    session = None
    try:
        engine = create_engine(
            get_database_url(),
            connect_args={"check_same_thread": False},  # Required for SQLite
            pool_pre_ping=True,  # Enable connection health checks
            pool_recycle=3600  # Recycle connections after 1 hour
        )
        
        # Test database connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Initialize default data sources
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check if data sources already exist
        if not session.query(DataSource).first():
            default_sources = [
                DataSource(
                    name="Google Places API",
                    source_type="api",
                    reliability_score=0.9,
                    config={"api_key_required": True}
                ),
                DataSource(
                    name="OpenStreetMap",
                    source_type="osm",
                    reliability_score=0.7,
                    config={"overpass_api": "https://overpass-api.de/api/interpreter"}
                ),
                DataSource(
                    name="Local Council CSV",
                    source_type="csv",
                    reliability_score=0.8,
                    config={"file_format": "csv"}
                ),
                DataSource(
                    name="Manual Entry",
                    source_type="manual",
                    reliability_score=1.0,
                    config={"requires_human_verification": True}
                )
            ]
            
            for source in default_sources:
                session.add(source)
            
            session.commit()
            print("Database initialized with default data sources")
    except Exception as e:
        print(f"Error initializing database: {e}")
        session.rollback()
    finally:
        session.close()

# Create simple database engine for SQLite
engine = create_engine(
    get_database_url(),
    connect_args={"check_same_thread": False}  # Allow cross-thread usage for SQLite
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get database session with proper error handling"""
    db = SessionLocal()
    try:
        # Verify connection is alive
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        db.rollback()
        raise
    finally:
        try:
            db.close()
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")
            pass  # Ensure we don't raise an error during cleanup

def get_session():
    """Get database session for direct use"""
    return SessionLocal()

def get_db_session():
    """Get a new database session"""
    return SessionLocal()

if __name__ == "__main__":
    init_database()