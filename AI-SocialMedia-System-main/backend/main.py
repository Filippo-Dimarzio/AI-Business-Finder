"""
FastAPI backend for the Business Finder system.
Provides REST API endpoints for the React frontend.
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel, ValidationError
from datetime import datetime
import os
import traceback
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from database import get_db, Business, ProcessingLog, init_database
from loguru import logger

# Configure logging
logger.add("api.log", rotation="500 MB", level="INFO")

class BusinessResponse(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    website_present: Optional[bool] = None
    website_url: Optional[str] = None
    social_present: Optional[bool] = None
    social_links: Optional[dict] = None
    no_website_no_social: Optional[bool] = None
    confidence_score: Optional[float] = None
    sources: Optional[List[str]] = None
    last_checked_date: Optional[datetime] = None
    human_review: Optional[str] = None
    human_reviewer: Optional[str] = None
    human_review_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class BusinessUpdate(BaseModel):
    human_review: Optional[str] = None
    human_reviewer: Optional[str] = None
    human_review_date: Optional[datetime] = None
    notes: Optional[str] = None

# Initialize FastAPI app
app = FastAPI(
    title="Business Finder API",
    description="API for finding businesses without website or social media presence",
    version="1.0.0"
)

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database error: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal database error occurred"}
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    logger.warning(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"}
    )

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database initialization handler
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        init_database()
        print("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

# API Routes
@app.get("/")
def root():
    return {"message": "Business Finder API", "version": "1.0.0"}

@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint for monitoring and load balancers."""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "degraded", "database": "error", "message": str(e)}

@app.get("/api/businesses", response_model=List[BusinessResponse])
def get_businesses(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    confidence_min: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Get list of businesses with optional filtering"""
    query = db.query(Business)
    
    # Apply filters
    if status:
        query = query.filter(Business.human_review == status)
    
    if confidence_min is not None:
        query = query.filter(Business.confidence_score >= confidence_min)
    
    # Apply pagination
    businesses = query.offset(skip).limit(limit).all()
    
    return businesses

@app.get("/api/businesses/{business_id}", response_model=BusinessResponse)
def get_business(business_id: int, db: Session = Depends(get_db)):
    """Get specific business by ID"""
    business = db.query(Business).filter(Business.id == business_id).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return business

@app.patch("/api/businesses/{business_id}", response_model=BusinessResponse)
def update_business(
    business_id: int,
    business_update: BusinessUpdate,
    db: Session = Depends(get_db)
):
    """Update business information"""
    business = db.query(Business).filter(Business.id == business_id).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Update fields
    update_data = business_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(business, field, value)
    
    business.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        db.refresh(business)
        return business
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating business: {str(e)}")

@app.get("/api/businesses/{business_id}/logs")
def get_business_logs(business_id: int, db: Session = Depends(get_db)):
    """Get processing logs for a specific business"""
    logs = db.query(ProcessingLog).filter(
        ProcessingLog.business_id == business_id
    ).order_by(ProcessingLog.timestamp.desc()).all()
    
    return logs

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get system statistics"""
    total_businesses = db.query(Business).count()
    pending_review = db.query(Business).filter(Business.human_review.is_(None)).count()
    approved = db.query(Business).filter(Business.human_review == 'approved').count()
    rejected = db.query(Business).filter(Business.human_review == 'rejected').count()
    high_confidence = db.query(Business).filter(Business.confidence_score >= 0.8).count()
    no_website_no_social = db.query(Business).filter(Business.no_website_no_social == True).count()
    
    return {
        "total_businesses": total_businesses,
        "pending_review": pending_review,
        "approved": approved,
        "rejected": rejected,
        "high_confidence": high_confidence,
        "no_website_no_social": no_website_no_social
    }

@app.post("/api/businesses/{business_id}/approve")
def approve_business(business_id: int, db: Session = Depends(get_db)):
    """Approve a business (mark as having no website/social media)"""
    business = db.query(Business).filter(Business.id == business_id).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    business.human_review = 'approved'
    business.human_review_date = datetime.utcnow()
    business.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        return {"message": "Business approved successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error approving business: {str(e)}")

@app.post("/api/businesses/{business_id}/reject")
def reject_business(business_id: int, db: Session = Depends(get_db)):
    """Reject a business (mark as having website/social media)"""
    business = db.query(Business).filter(Business.id == business_id).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    business.human_review = 'rejected'
    business.human_review_date = datetime.utcnow()
    business.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        return {"message": "Business rejected successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error rejecting business: {str(e)}")

@app.get("/api/export/csv")
def export_csv(
    status: Optional[str] = None,
    confidence_min: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Export businesses to CSV format"""
    query = db.query(Business)
    
    # Apply filters
    if status:
        query = query.filter(Business.human_review == status)
    
    if confidence_min is not None:
        query = query.filter(Business.confidence_score >= confidence_min)
    
    businesses = query.all()
    
    # Convert to CSV format
    csv_data = []
    for business in businesses:
        csv_data.append({
            'id': business.id,
            'name': business.name,
            'address': business.address or '',
            'phone': business.phone or '',
            'city': business.city or '',
            'postcode': business.postcode or '',
            'website_present': business.website_present or False,
            'website_url': business.website_url or '',
            'social_present': business.social_present or False,
            'social_links': business.social_links or {},
            'no_website_no_social': business.no_website_no_social or False,
            'confidence_score': business.confidence_score or 0,
            'sources': business.sources or [],
            'last_checked_date': business.last_checked_date or '',
            'human_review': business.human_review or '',
            'notes': business.notes or ''
        })
    
    return csv_data


@app.post('/api/retrain')
def retrain_model(db: Session = Depends(get_db)):
    """Trigger ML retraining using labeled data and reclassify businesses."""
    # Import classifier lazily and handle missing deps so frontend can still call this endpoint when
    # the ML stack isn't fully installed in the environment.
    try:
        from classifier import BusinessClassifier
    except ModuleNotFoundError as e:
        return {"status": "error", "message": f"Missing dependency: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Cannot import classifier: {str(e)}"}

    try:
        classifier = BusinessClassifier()
    except Exception as e:
        return {"status": "error", "message": f"Failed to initialize classifier: {str(e)}"}

    X, y = classifier.prepare_training_data()

    if len(X) == 0:
        # Not enough labeled data - return helpful message
        try:
            classifier.close()
        except Exception:
            pass
        return {"status": "not_enough_data", "message": "Not enough labeled data to train (need at least 10)."}

    try:
        metrics = classifier.train_model(X, y)
        # Clean metrics to ensure they're JSON-serializable (handle NaN/Inf)
        import math
        cleaned_metrics = {}
        for k, v in (metrics or {}).items():
            if isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    cleaned_metrics[k] = None
                else:
                    cleaned_metrics[k] = v
            else:
                cleaned_metrics[k] = v
        
        # Save and classify
        classifier.save_model()
        processed = classifier.classify_all_businesses()
    except Exception as e:
        return {"status": "error", "message": f"Training failed: {str(e)}"}
    finally:
        try:
            classifier.close()
        except Exception:
            pass

    return {"status": "ok", "metrics": cleaned_metrics, "reclassified": processed}


@app.post('/api/admin/seed_labels')
def seed_demo_labels(count: int = 10, x_admin_key: str = None, db: Session = Depends(get_db)):
    """Seed demo human labels for the dataset so retraining can be demonstrated.

    This endpoint only runs when the DEMO_ALLOW_SEED environment variable is set to
    a truthy value ("1", "true", "yes"), OR when a valid ADMIN_API_KEY is provided.
    
    For production, provide the X-Admin-Key header with the ADMIN_API_KEY from env vars.
    For development, set DEMO_ALLOW_SEED=true.
    """
    allow_seed = os.getenv("DEMO_ALLOW_SEED", "false").lower()
    admin_key = os.getenv("ADMIN_API_KEY", "")
    
    # Check if demo seeding is allowed or if correct admin key is provided
    demo_mode = allow_seed in ("1", "true", "yes")
    has_valid_key = admin_key and x_admin_key == admin_key
    
    if not (demo_mode or has_valid_key):
        raise HTTPException(status_code=403, detail="Demo seeding is disabled. Set DEMO_ALLOW_SEED=true or provide a valid X-Admin-Key header.")

    # Select unlabeled businesses
    to_seed = db.query(Business).filter(Business.human_review.is_(None)).limit(count).all()

    if not to_seed:
        return {"seeded": 0, "message": "No unlabeled businesses available"}

    seeded = {"approved": 0, "rejected": 0}
    seeded_ids = []
    for b in to_seed:
        # Simple deterministic rule: high confidence -> approved, otherwise rejected
        if (b.confidence_score or 0) >= 0.6:
            b.human_review = 'approved'
            seeded['approved'] += 1
        else:
            b.human_review = 'rejected'
            seeded['rejected'] += 1
        b.human_reviewer = 'demo-seeder'
        b.human_review_date = datetime.utcnow()
        b.updated_at = datetime.utcnow()
        seeded_ids.append(b.id)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to seed labels: {str(e)}")

    return {"seeded": sum(seeded.values()), "breakdown": seeded, "ids": seeded_ids}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)