"""
Enhanced pipeline script that ensures all steps run properly.
"""

import os
import sys
from datetime import datetime
import requests
from loguru import logger
from database import init_database, get_session, Business
from classifier import BusinessClassifier
from enhanced_website_checker import EnhancedWebsiteChecker
from social_checker import SocialMediaChecker

def verify_google_places_api():
    """Verify Google Places API key is working"""
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        logger.error("GOOGLE_PLACES_API_KEY not set in .env file")
        return False
        
    # Test the API key with the new Places API
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName"
    }
    data = {
        "textQuery": "Restaurant in Lisbon"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if "places" in result:
            logger.info("Google Places API key verified successfully")
            return True
        else:
            logger.error(f"Google Places API key verification failed: {result.get('error', {}).get('message')}")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying Google Places API key: {e}")
        return False

def update_websites():
    """Update website information for all businesses"""
    checker = EnhancedWebsiteChecker()
    try:
        processed_count = checker.check_all_businesses()
        logger.info(f"Updated website info for {processed_count} businesses")
    except Exception as e:
        logger.error(f"Error in website checking: {e}")
    finally:
        checker.close()

def update_social_media():
    """Update social media information for all businesses"""
    session = get_session()
    checker = SocialMediaChecker()
    
    businesses = session.query(Business).filter(
        (Business.social_present.is_(None)) |  # Never checked
        (Business.last_checked_date.is_(None))  # Never checked
    ).all()
    
    for business in businesses:
        try:
            checker.check_business(business)
            logger.info(f"Updated social media info for {business.name}")
            session.commit()
        except Exception as e:
            logger.error(f"Error checking social media for {business.name}: {e}")
            session.rollback()
            
    session.close()

def train_and_classify():
    """Train ML model and classify businesses"""
    classifier = BusinessClassifier()
    
    # Prepare training data
    logger.info("Preparing training data")
    X, y = classifier.prepare_training_data()
    
    if len(X) > 0:
        # Train model
        logger.info("Training ML model")
        metrics = classifier.train_model(X, y)
        logger.info(f"Model training completed: {metrics}")
        
        # Save model
        classifier.save_model("business_classifier_model.pkl")
        
        # Classify all businesses
        logger.info("Classifying all businesses")
        classified_count = classifier.classify_all_businesses()
        logger.info(f"Classification completed for {classified_count} businesses")
    else:
        logger.warning("No training data available. Using rule-based classification")
        classifier.run_rule_based_classification()
    
    classifier.close()

def main():
    """Main entry point"""
    # Configure logging
    logger.remove()
    logger.add(sys.stdout, level="INFO")
    logger.add("enhanced_pipeline.log", level="DEBUG")
    
    try:
        # Step 1: Initialize database
        logger.info("Initializing database")
        init_database()
        
        # Step 2: Verify Google Places API
        logger.info("Verifying Google Places API")
        if not verify_google_places_api():
            logger.warning("Google Places API verification failed. Continuing with limited functionality.")
        
        # Step 3: Update website information
        logger.info("Updating website information")
        update_websites()
        
        # Step 4: Update social media information
        logger.info("Updating social media information")
        update_social_media()
        
        # Step 5: Train model and classify businesses
        logger.info("Training model and classifying businesses")
        train_and_classify()
        
        logger.info("Enhanced pipeline completed successfully")
        
    except Exception as e:
        logger.error(f"Enhanced pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()