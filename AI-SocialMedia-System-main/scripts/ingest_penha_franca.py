"""
Data ingestion script for Penha de França area businesses.
Uses both OpenStreetMap and Google Places API for comprehensive coverage.
"""

from ingest import DataIngester
from database import SessionLocal, Business, init_database
from datetime import datetime
import googlemaps
import os
from dotenv import load_dotenv
from loguru import logger
import time
from typing import List, Dict

load_dotenv()

# Penha de França area boundaries
PENHA_FRANCA_AREA = {
    "name": "Penha de França",
    "bbox": (38.7250, -9.1350, 38.7310, -9.1280),  # (min_lat, min_lon, max_lat, max_lon)
    "center": {
        "lat": 38.7280,
        "lng": -9.1315
    }
}

# Extended business types to include more variety
BUSINESS_TYPES = [
    'restaurant',
    'cafe',
    'bar',
    'bakery',
    'food',
    'meal_delivery',
    'meal_takeaway',
    'supermarket',
    'convenience_store',
    'grocery_store',
    'liquor_store',
    'night_club'
]

class PenhaFrancaIngester:
    def __init__(self):
        self.ingester = DataIngester()
        self.gmaps = googlemaps.Client(key=os.getenv('GOOGLE_PLACES_API_KEY'))
        self.session = SessionLocal()
    
    def ingest_from_google_places(self) -> List[Dict]:
        """
        Ingest businesses using Google Places API
        """
        logger.info("Starting Google Places ingestion for Penha de França area")
        
        all_businesses = []
        
        try:
            for business_type in BUSINESS_TYPES:
                # Search for each business type
                places_result = self.gmaps.places_nearby(
                    location=PENHA_FRANCA_AREA["center"],
                    radius=500,  # 500 meters radius
                    type=business_type
                )
                
                if places_result.get('results'):
                    for place in places_result['results']:
                        try:
                            # Get detailed place information
                            place_details = self.gmaps.place(place['place_id'])['result']
                            
                            # Create business record
                            business_data = {
                                "name": place_details.get('name'),
                                "address": place_details.get('formatted_address'),
                                "city": "Lisboa",
                                "postcode": self._extract_postcode(place_details.get('formatted_address', '')),
                                "phone": place_details.get('formatted_phone_number'),
                                "website_present": bool(place_details.get('website')),
                                "website_url": place_details.get('website'),
                                "google_place_id": place['place_id'],
                                "google_rating": place_details.get('rating'),
                                "google_review_count": place_details.get('user_ratings_total'),
                                "google_photos_count": len(place_details.get('photos', [])),
                                "google_business_status": place_details.get('business_status'),
                                "google_types": place_details.get('types'),
                                "sources": ["google_places"],
                                "created_at": datetime.utcnow(),
                                "updated_at": datetime.utcnow()
                            }
                            
                            # Check if business already exists
                            existing = self.session.query(Business).filter(
                                Business.name == business_data["name"],
                                Business.address == business_data["address"]
                            ).first()
                            
                            if not existing:
                                business = Business(**business_data)
                                self.session.add(business)
                                all_businesses.append(business_data)
                                logger.info(f"Added new business: {business_data['name']}")
                            
                            # Sleep to avoid hitting API rate limits
                            time.sleep(2)
                            
                        except Exception as e:
                            logger.error(f"Error processing place {place.get('name')}: {e}")
                            continue
                
                self.session.commit()
                logger.info(f"Completed processing {business_type} businesses")
                
        except Exception as e:
            logger.error(f"Error in Google Places ingestion: {e}")
            self.session.rollback()
            raise
        
        return all_businesses
    
    def ingest_all_sources(self):
        """
        Ingest businesses from all available sources
        """
        try:
            # 1. First ingest from OpenStreetMap
            logger.info("Starting OpenStreetMap ingestion")
            osm_businesses = self.ingester.ingest_osm(
                bbox=PENHA_FRANCA_AREA["bbox"],
                business_types=BUSINESS_TYPES
            )
            logger.info(f"Ingested {len(osm_businesses)} businesses from OpenStreetMap")
            
            # 2. Then ingest from Google Places
            logger.info("Starting Google Places ingestion")
            google_businesses = self.ingest_from_google_places()
            logger.info(f"Ingested {len(google_businesses)} businesses from Google Places")
            
            # Print summary
            total = self.session.query(Business).count()
            logger.info(f"Total businesses in database: {total}")
            
            # Print sample of new businesses
            print("\nSample businesses from Penha de França:")
            businesses = self.session.query(Business).order_by(
                Business.created_at.desc()
            ).limit(10).all()
            
            for business in businesses:
                print(f"\nName: {business.name}")
                print(f"Address: {business.address or 'Not available'}")
                print(f"Website: {'Yes' if business.website_present else 'No'}")
                print(f"Google Rating: {business.google_rating or 'N/A'}")
                print(f"Source: {', '.join(business.sources)}")
        
        except Exception as e:
            logger.error(f"Error during ingestion: {e}")
            raise
        
        finally:
            self.close()
    
    def _extract_postcode(self, address: str) -> str:
        """Extract postcode from address string"""
        # Portuguese postcodes format: XXXX-XXX
        import re
        postcode_match = re.search(r'\d{4}-\d{3}', address)
        return postcode_match.group(0) if postcode_match else None
    
    def close(self):
        """Clean up resources"""
        self.session.close()
        self.ingester.close()

def main():
    """Main entry point"""
    logger.info("Starting Penha de França area business ingestion")
    
    ingester = PenhaFrancaIngester()
    try:
        ingester.ingest_all_sources()
    except Exception as e:
        logger.error(f"Failed to complete ingestion: {e}")
        raise

if __name__ == "__main__":
    main()