"""
Enhanced website checker using Google Places API v1
"""

import os
import requests
from datetime import datetime
from loguru import logger
from database import get_session, Business

class EnhancedWebsiteChecker:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        self.session = get_session()
    
    def check_business(self, business):
        """
        Check website and online presence for a business
        """
        try:
            if not business.name:
                logger.warning(f"Business {business.id} has no name, skipping check")
                return
            
            # Build search query
            search_query = business.name
            if business.address:
                search_query += f" {business.address}"
            if business.city:
                search_query += f" {business.city}"
            
            # Search for place
            search_url = "https://places.googleapis.com/v1/places:searchText"
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress"
            }
            search_data = {
                "textQuery": search_query
            }
            
            response = requests.post(search_url, headers=headers, json=search_data)
            result = response.json()
            
            if "places" in result and result["places"]:
                place = result["places"][0]
                place_id = place["id"]
                
                # Get place details
                details_url = f"https://places.googleapis.com/v1/places/{place_id}"
                details_headers = {
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": "websiteUri,formattedPhoneNumber,photos,rating,userRatingCount,primaryType,secondaryTypes,businessStatus,regularHours,editorialSummary,priceLevel"
                }
                
                details_response = requests.get(details_url, headers=details_headers)
                details = details_response.json()
                
                # Update business record
                if details.get("websiteUri"):
                    business.website_url = details["websiteUri"]
                    business.website_present = True
                    logger.info(f"Found website for {business.name}: {business.website_url}")
                
                if details.get("formattedPhoneNumber"):
                    business.phone = details["formattedPhoneNumber"]
                
                # Update additional Google-specific data
                business.google_photos_count = len(details.get("photos", []))
                business.google_rating = details.get("rating", 0)
                business.google_review_count = details.get("userRatingCount", 0)
                business.google_place_id = place_id
                business.google_business_status = details.get("businessStatus")
                
                # Store detailed findings
                digital_presence = {
                    "has_website": bool(details.get("websiteUri")),
                    "has_phone": bool(details.get("formattedPhoneNumber")),
                    "has_photos": business.google_photos_count > 0,
                    "has_reviews": business.google_review_count > 0,
                    "business_type": details.get("primaryType"),
                    "additional_types": details.get("secondaryTypes", []),
                    "has_hours": bool(details.get("regularHours")),
                    "price_level": details.get("priceLevel"),
                    "has_description": bool(details.get("editorialSummary")),
                    "verification_date": datetime.utcnow().isoformat()
                }
                
                business.digital_presence_details = digital_presence
                
                # Update sources
                if business.sources and "Google Places API" not in business.sources:
                    business.sources.append("Google Places API")
                elif not business.sources:
                    business.sources = ["Google Places API"]
                
                business.last_checked_date = datetime.utcnow()
                logger.info(f"Successfully updated information for {business.name}")
                
            else:
                logger.warning(f"No Google Places data found for {business.name}")
                
        except Exception as e:
            logger.error(f"Error checking business {business.name}: {e}")
            raise
    
    def check_all_businesses(self):
        """Check all businesses that haven't been checked recently"""
        businesses = self.session.query(Business).filter(
            (Business.website_present.is_(None)) |  # Never checked
            (Business.last_checked_date.is_(None))  # Never checked
        ).all()
        
        processed_count = 0
        for business in businesses:
            try:
                self.check_business(business)
                processed_count += 1
                
                if processed_count % 10 == 0:
                    self.session.commit()
                    logger.info(f"Processed {processed_count} businesses")
                    
            except Exception as e:
                logger.error(f"Error processing business {business.id}: {e}")
                self.session.rollback()
                continue
        
        self.session.commit()
        return processed_count
    
    def close(self):
        """Close database session"""
        self.session.close()