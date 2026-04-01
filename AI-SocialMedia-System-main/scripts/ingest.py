"""
Data ingestion module for the Business Finder system.
Handles CSV files, Google Places API, and OpenStreetMap data.
"""

import pandas as pd
import requests
import json
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from loguru import logger
from database import SessionLocal, Business, DataSource, ProcessingLog, BusinessStatus

def get_session():
    return SessionLocal()
import googlemaps
from dotenv import load_dotenv

load_dotenv()

class DataIngester:
    """Main class for ingesting data from various sources"""
    
    def __init__(self):
        self.session = get_session()
        self.gmaps = None
        self._init_google_maps()
        
    def _init_google_maps(self):
        """Initialize Google Maps client if API key is available"""
        api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        try:
            if api_key and api_key != "your_actual_api_key_here":
                self.gmaps = googlemaps.Client(key=api_key)
                logger.info("Google Maps client initialized")
            else:
                logger.warning("Google Places API key not found. Google Places search will be disabled.")
                self.gmaps = None
        except Exception as e:
            logger.error(f"Error initializing Google Maps client: {e}")
            self.gmaps = None
    
    def ingest_csv(self, file_path: str, source_name: str = "CSV Import") -> List[Dict]:
        """
        Ingest business data from CSV file
        
        Args:
            file_path: Path to CSV file
            source_name: Name of the data source
            
        Returns:
            List of ingested business records
        """
        logger.info(f"Starting CSV ingestion from {file_path}")
        
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            logger.info(f"Loaded {len(df)} rows from CSV")
            
            # Expected columns (flexible mapping)
            required_columns = ['name', 'address']
            optional_columns = ['phone', 'city', 'postcode', 'website', 'social_media']
            
            # Check for required columns
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            ingested_businesses = []
            
            for index, row in df.iterrows():
                try:
                    business_data = {
                        'name': str(row['name']).strip(),
                        'address': str(row['address']).strip() if pd.notna(row['address']) else None,
                        'phone': str(row['phone']).strip() if 'phone' in row and pd.notna(row['phone']) else None,
                        'city': str(row['city']).strip() if 'city' in row and pd.notna(row['city']) else None,
                        'postcode': str(row['postcode']).strip() if 'postcode' in row and pd.notna(row['postcode']) else None,
                        'sources': [source_name],
                        'created_at': datetime.utcnow(),
                        'status': BusinessStatus.PENDING
                    }
                    
                    # Check if business already exists
                    existing = self._find_existing_business(business_data)
                    if existing:
                        logger.info(f"Business already exists: {business_data['name']}")
                        continue
                    
                    # Create new business record
                    business = Business(**business_data)
                    self.session.add(business)
                    ingested_businesses.append(business_data)
                    
                    # Log the ingestion
                    self._log_processing(
                        business_id=business.id,
                        process_type="csv_ingest",
                        status="success",
                        message=f"Successfully ingested {business_data['name']}"
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing row {index}: {e}")
                    self._log_processing(
                        business_id=None,
                        process_type="csv_ingest",
                        status="error",
                        message=f"Error processing row {index}: {str(e)}"
                    )
            
            self.session.commit()
            logger.info(f"Successfully ingested {len(ingested_businesses)} businesses from CSV")
            return ingested_businesses
            
        except Exception as e:
            logger.error(f"Error ingesting CSV: {e}")
            self.session.rollback()
            raise
    
    def ingest_google_places(self, query: str, location: str = None, radius: int = 5000) -> List[Dict]:
        """
        Ingest business data from Google Places API
        
        Args:
            query: Search query (e.g., "restaurants", "cafes", "takeaways")
            location: Location to search around (e.g., "London, UK")
            radius: Search radius in meters
            
        Returns:
            List of ingested business records
        """
        if not self.gmaps:
            logger.error("Google Maps client not initialized")
            return []
        
        logger.info(f"Starting Google Places search for '{query}' in '{location}'")
        
        try:
            # Search for places
            places_result = self.gmaps.places_nearby(
                location=location,
                radius=radius,
                keyword=query,
                type='restaurant'  # Focus on food businesses
            )
            
            ingested_businesses = []
            
            for place in places_result.get('results', []):
                try:
                    # Get detailed information
                    place_details = self.gmaps.place(
                        place_id=place['place_id'],
                        fields=['name', 'formatted_address', 'formatted_phone_number', 
                               'website', 'types', 'rating', 'user_ratings_total']
                    )
                    
                    details = place_details.get('result', {})
                    
                    business_data = {
                        'name': details.get('name', ''),
                        'address': details.get('formatted_address', ''),
                        'phone': details.get('formatted_phone_number', ''),
                        'website_url': details.get('website', ''),
                        'sources': ['Google Places API'],
                        'created_at': datetime.utcnow()
                    }
                    
                    # Extract city and postcode from address
                    address_parts = business_data['address'].split(',')
                    if len(address_parts) >= 2:
                        business_data['city'] = address_parts[-2].strip()
                        business_data['postcode'] = address_parts[-1].strip()
                    
                    # Check if business already exists
                    existing = self._find_existing_business(business_data)
                    if existing:
                        logger.info(f"Business already exists: {business_data['name']}")
                        continue
                    
                    # Create new business record
                    business = Business(**business_data)
                    self.session.add(business)
                    ingested_businesses.append(business_data)
                    
                    # Log the ingestion
                    self._log_processing(
                        business_id=business.id,
                        process_type="google_places_ingest",
                        status="success",
                        message=f"Successfully ingested {business_data['name']}"
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing Google Places result: {e}")
                    self._log_processing(
                        business_id=None,
                        process_type="google_places_ingest",
                        status="error",
                        message=f"Error processing Google Places result: {str(e)}"
                    )
            
            self.session.commit()
            logger.info(f"Successfully ingested {len(ingested_businesses)} businesses from Google Places")
            return ingested_businesses
            
        except Exception as e:
            logger.error(f"Error ingesting Google Places data: {e}")
            self.session.rollback()
            raise
    
    def ingest_osm(self, bbox: tuple, business_types: List[str] = None) -> List[Dict]:
        """
        Ingest business data from OpenStreetMap using Overpass API
        
        Args:
            bbox: Bounding box as (min_lat, min_lon, max_lat, max_lon)
            business_types: List of OSM business types to search for
            
        Returns:
            List of ingested business records
        """
        if business_types is None:
            business_types = ['restaurant', 'cafe', 'fast_food', 'bakery', 'pub', 'bar']
        
        logger.info(f"Starting OSM ingestion for bbox {bbox}")
        
        try:
            # Build Overpass query
            query = self._build_overpass_query(bbox, business_types)
            
            # Make request to Overpass API
            response = requests.post(
                'https://overpass-api.de/api/interpreter',
                data={'data': query},
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            ingested_businesses = []
            
            for element in data.get('elements', []):
                try:
                    tags = element.get('tags', {})
                    
                    business_data = {
                        'name': tags.get('name', ''),
                        'address': self._format_osm_address(tags),
                        'phone': tags.get('phone', ''),
                        'city': tags.get('addr:city', ''),
                        'postcode': tags.get('addr:postcode', ''),
                        'sources': ['OpenStreetMap'],
                        'created_at': datetime.utcnow()
                    }
                    
                    # Skip if no name
                    if not business_data['name']:
                        continue
                    
                    # Check if business already exists
                    existing = self._find_existing_business(business_data)
                    if existing:
                        logger.info(f"Business already exists: {business_data['name']}")
                        continue
                    
                    # Create new business record
                    business = Business(**business_data)
                    self.session.add(business)
                    ingested_businesses.append(business_data)
                    
                    # Log the ingestion
                    self._log_processing(
                        business_id=business.id,
                        process_type="osm_ingest",
                        status="success",
                        message=f"Successfully ingested {business_data['name']}"
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing OSM element: {e}")
                    self._log_processing(
                        business_id=None,
                        process_type="osm_ingest",
                        status="error",
                        message=f"Error processing OSM element: {str(e)}"
                    )
            
            self.session.commit()
            logger.info(f"Successfully ingested {len(ingested_businesses)} businesses from OSM")
            return ingested_businesses
            
        except Exception as e:
            logger.error(f"Error ingesting OSM data: {e}")
            self.session.rollback()
            raise
    
    def _find_existing_business(self, business_data: Dict) -> Optional[Business]:
        """Check if business already exists in database"""
        return self.session.query(Business).filter(
            Business.name == business_data['name'],
            Business.address == business_data['address']
        ).first()
    
    def _log_processing(self, business_id: Optional[int], process_type: str, 
                       status: str, message: str, details: Dict = None):
        """Log processing activities"""
        log_entry = ProcessingLog(
            business_id=business_id,
            process_type=process_type,
            status=status,
            message=message,
            details=details
        )
        self.session.add(log_entry)
    
    def _build_overpass_query(self, bbox: tuple, business_types: List[str]) -> str:
        """Build Overpass API query for business types"""
        min_lat, min_lon, max_lat, max_lon = bbox
        
        query = f"""
        [out:json][timeout:60];
        (
        """
        
        for business_type in business_types:
            query += f"""
          node["amenity"="{business_type}"]({min_lat},{min_lon},{max_lat},{max_lon});
          way["amenity"="{business_type}"]({min_lat},{min_lon},{max_lat},{max_lon});
          relation["amenity"="{business_type}"]({min_lat},{min_lon},{max_lat},{max_lon});
            """
        
        query += """
        );
        out body;
        """
        
        return query
    
    def _format_osm_address(self, tags: Dict) -> str:
        """Format OSM address from tags"""
        address_parts = []
        
        if tags.get('addr:housenumber') and tags.get('addr:street'):
            address_parts.append(f"{tags['addr:housenumber']} {tags['addr:street']}")
        elif tags.get('addr:street'):
            address_parts.append(tags['addr:street'])
        
        if tags.get('addr:city'):
            address_parts.append(tags['addr:city'])
        
        if tags.get('addr:postcode'):
            address_parts.append(tags['addr:postcode'])
        
        return ', '.join(address_parts) if address_parts else ''
    
    def close(self):
        """Close database session"""
        self.session.close()

# Example usage and testing
if __name__ == "__main__":
    ingester = DataIngester()
    
    try:
        # Ingest from CSV file
        ingester.ingest_csv("all_businesses.csv", "CSV Import")
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
    finally:
        ingester.close()
