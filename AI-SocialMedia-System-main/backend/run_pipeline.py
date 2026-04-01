"""
Main orchestration script for the Business Finder system.
Runs the complete pipeline: ingest -> normalize -> website check -> social check -> classify -> export
"""

import os
import sys
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

# Import all modules
from database import init_database
from ingest import DataIngester
from normalize import DataNormalizer
from website_checker import WebsiteChecker
from social_checker import SocialMediaChecker
from classifier import BusinessClassifier
from export import BusinessExporter

# Load environment variables
load_dotenv()

class BusinessFinderPipeline:
    """Main pipeline orchestrator"""
    
    def __init__(self):
        self.ingester = DataIngester()
        self.normalizer = DataNormalizer()
        self.website_checker = WebsiteChecker()
        self.social_checker = SocialMediaChecker()
        self.classifier = BusinessClassifier()
        self.exporter = BusinessExporter()
        
        # Pipeline configuration
        self.config = {
            'skip_ingestion': os.getenv('SKIP_INGESTION', 'false').lower() == 'true',
            'skip_website_check': os.getenv('SKIP_WEBSITE_CHECK', 'false').lower() == 'true',
            'skip_social_check': os.getenv('SKIP_SOCIAL_CHECK', 'false').lower() == 'true',
            'skip_classification': os.getenv('SKIP_CLASSIFICATION', 'false').lower() == 'true',
            'confidence_threshold': float(os.getenv('CONFIDENCE_THRESHOLD', '0.7'))
        }
    
    def run_complete_pipeline(self):
        """Run the complete business finding pipeline"""
        logger.info("Starting Business Finder Pipeline")
        start_time = datetime.now()
        
        try:
            # Step 1: Initialize database
            logger.info("Step 1: Initializing database")
            init_database()
            
            # Step 2: Data ingestion
            if not self.config['skip_ingestion']:
                logger.info("Step 2: Data ingestion")
                self.run_ingestion()
            else:
                logger.info("Step 2: Skipping data ingestion")
            
            # Step 3: Data normalization and deduplication
            logger.info("Step 3: Data normalization and deduplication")
            self.run_normalization()
            
            # Step 4: Website detection
            if not self.config['skip_website_check']:
                logger.info("Step 4: Website detection")
                self.run_website_check()
            else:
                logger.info("Step 4: Skipping website check")
            
            # Step 5: Social media detection
            if not self.config['skip_social_check']:
                logger.info("Step 5: Social media detection")
                self.run_social_check()
            else:
                logger.info("Step 5: Skipping social media check")
            
            # Step 6: ML classification
            if not self.config['skip_classification']:
                logger.info("Step 6: ML classification")
                self.run_classification()
            else:
                logger.info("Step 6: Skipping classification")
            
            # Step 7: Export results
            logger.info("Step 7: Exporting results")
            self.run_export()
            
            # Pipeline completed
            end_time = datetime.now()
            duration = end_time - start_time
            logger.info(f"Pipeline completed successfully in {duration}")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
    
    def run_ingestion(self):
        """Run data ingestion from various sources"""
        try:
            # Ingest from sample CSV if it exists
            sample_csv_path = "sample_data.csv"
            if os.path.exists(sample_csv_path):
                logger.info("Ingesting from sample CSV")
                self.ingester.ingest_csv(sample_csv_path, "Sample Data")
            
            # Ingest from Google Places API (if configured)
            google_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
            if google_api_key and google_api_key != "your_google_places_api_key_here":
                logger.info("Ingesting from Google Places API")
                # Example: search for restaurants in London
                self.ingester.ingest_google_places("restaurants", "London, UK", 5000)
                self.ingester.ingest_google_places("cafes", "London, UK", 5000)
                self.ingester.ingest_google_places("takeaways", "London, UK", 5000)
            
            # Ingest from OpenStreetMap (if configured)
            logger.info("Ingesting from OpenStreetMap")
            # Example: London bounding box
            london_bbox = (51.5074, -0.1278, 51.5074, -0.1278)  # Simplified for demo
            self.ingester.ingest_osm(london_bbox)
            
        except Exception as e:
            logger.error(f"Error in data ingestion: {e}")
            raise
    
    def run_normalization(self):
        """Run data normalization and deduplication"""
        try:
            # Normalize all business data
            logger.info("Normalizing business data")
            self.normalizer.normalize_all_businesses()
            
            # Find and merge duplicates
            logger.info("Finding and merging duplicates")
            duplicates = self.normalizer.find_duplicates(threshold=0.8)
            if duplicates:
                merged_count = self.normalizer.merge_duplicates(duplicates)
                logger.info(f"Merged {merged_count} duplicate businesses")
            else:
                logger.info("No duplicates found")
            
        except Exception as e:
            logger.error(f"Error in data normalization: {e}")
            raise
    
    def run_website_check(self):
        """Run website detection for all businesses using both direct checks and Google Places API"""
        try:
            from database import get_session, Business
            import requests
            import time
            
            google_api_key = os.getenv('GOOGLE_PLACES_API_KEY')
            if not google_api_key or google_api_key == 'your_google_places_api_key_here':
                logger.warning("Google Places API key not configured, skipping API verification")
                # Fallback to regular website check
                processed_count = self.website_checker.check_all_businesses()
                logger.info(f"Website check completed for {processed_count} businesses")
                return
                
            session = get_session()
            businesses = session.query(Business).filter(
                (Business.website_present.is_(None)) |  # Never checked
                (Business.last_checked_date.is_(None))  # Never checked
            ).all()
            
            processed_count = 0
            for business in businesses:
                try:
                    # Step 1: Regular website check
                    self.website_checker.check_business(business)
                    
                    # Step 2: Google Places verification
                    search_query = f"{business.name} {business.address} {business.city}"
                    
                    # Search for place
                    search_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
                    search_params = {
                        'input': search_query,
                        'inputtype': 'textquery',
                        'fields': 'place_id',
                        'key': google_api_key
                    }
                    
                    response = requests.get(search_url, params=search_params)
                    result = response.json()
                    
                    if result.get('status') == 'OK' and result.get('candidates'):
                        place_id = result['candidates'][0]['place_id']
                        
                        # Get details
                        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                        details_params = {
                            'place_id': place_id,
                            'fields': 'website,formatted_phone_number,photos,reviews,rating,business_status,user_ratings_total',
                            'key': google_api_key
                        }
                        
                        details_response = requests.get(details_url, params=details_params)
                        place_details = details_response.json().get('result', {})
                        
                        # Update business record
                        if place_details.get('website'):
                            business.website_url = place_details['website']
                            business.website_present = True
                        
                        if place_details.get('formatted_phone_number'):
                            business.phone = place_details['formatted_phone_number']
                        
                        # Add Google-specific data for ML features
                        business.google_photos_count = len(place_details.get('photos', []))
                        business.google_review_count = place_details.get('user_ratings_total', 0)
                        business.google_rating = place_details.get('rating', 0)
                        
                        # Update sources
                        if business.sources and 'Google Places API' not in business.sources:
                            business.sources.append('Google Places API')
                        elif not business.sources:
                            business.sources = ['Google Places API']
                    
                    processed_count += 1
                    if processed_count % 10 == 0:
                        logger.info(f"Processed {processed_count} businesses")
                        session.commit()
                    
                    # Respect API rate limits
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error checking business {business.id}: {e}")
                    continue
            
            session.commit()
            logger.info(f"Website check completed for {processed_count} businesses")
            
        except Exception as e:
            logger.error(f"Error in website check: {e}")
            raise
    
    def run_social_check(self):
        """Run social media detection for all businesses"""
        try:
            # Check social media for all businesses
            processed_count = self.social_checker.check_all_businesses()
            logger.info(f"Social media check completed for {processed_count} businesses")
            
        except Exception as e:
            logger.error(f"Error in social media check: {e}")
            raise
    
    def run_classification(self):
        """Run ML classification"""
        try:
            # Prepare training data
            logger.info("Preparing training data")
            X, y = self.classifier.prepare_training_data()
            
            if len(X) > 0:
                # Train model
                logger.info("Training ML model")
                metrics = self.classifier.train_model(X, y)
                logger.info(f"Model training completed: {metrics}")
                
                # Save model
                self.classifier.save_model("business_classifier_model.pkl")
                
                # Classify all businesses
                logger.info("Classifying all businesses")
                classified_count = self.classifier.classify_all_businesses()
                logger.info(f"Classification completed for {classified_count} businesses")
            else:
                logger.warning("No training data available. Skipping model training.")
                
                # Use rule-based classification as fallback
                logger.info("Using rule-based classification")
                self.run_rule_based_classification()
            
        except Exception as e:
            logger.error(f"Error in classification: {e}")
            raise
    
    def run_rule_based_classification(self):
        """Run rule-based classification as fallback"""
        try:
            from database import get_session, Business
            
            session = get_session()
            businesses = session.query(Business).all()
            
            for business in businesses:
                # Simple rule-based classification
                has_website = business.website_present or False
                has_social = business.social_present or False
                
                # Classify as no website/social if both are False
                business.no_website_no_social = not has_website and not has_social
                
                # Calculate confidence based on data completeness
                confidence = 0.5  # Base confidence
                if business.address:
                    confidence += 0.1
                if business.phone:
                    confidence += 0.1
                if business.sources and len(business.sources) > 1:
                    confidence += 0.1
                
                business.confidence_score = min(confidence, 1.0)
                business.last_checked_date = datetime.utcnow()
            
            session.commit()
            session.close()
            logger.info(f"Rule-based classification completed for {len(businesses)} businesses")
            
        except Exception as e:
            logger.error(f"Error in rule-based classification: {e}")
            raise
    
    def run_export(self):
        """Export results"""
        try:
            # Export all businesses
            logger.info("Exporting all businesses")
            self.exporter.export_to_csv("all_businesses.csv")
            self.exporter.export_to_json("all_businesses.json")
            
            # Export approved businesses only
            logger.info("Exporting approved businesses")
            self.exporter.export_approved_only("approved_businesses.csv")
            
            # Export high confidence predictions
            logger.info("Exporting high confidence predictions")
            self.exporter.export_high_confidence("high_confidence_businesses.csv", 
                                               confidence_threshold=self.config['confidence_threshold'])
            
            # Generate summary report
            logger.info("Generating summary report")
            self.exporter.export_summary_report("summary_report.json")
            
        except Exception as e:
            logger.error(f"Error in export: {e}")
            raise
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.ingester.close()
            self.normalizer.close()
            self.website_checker.close()
            self.social_checker.close()
            self.classifier.close()
            self.exporter.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def main():
    """Main entry point"""
    # Configure logging
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    logger.add("business_finder.log", level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    
    # Create and run pipeline
    pipeline = BusinessFinderPipeline()
    
    try:
        pipeline.run_complete_pipeline()
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)
    finally:
        pipeline.cleanup()

if __name__ == "__main__":
    main()
