"""
Data normalization and deduplication module for the Business Finder system.
Handles name normalization, address standardization, and duplicate detection.
"""

import re
import string
from typing import List, Dict, Tuple, Optional, Set
from difflib import SequenceMatcher
from loguru import logger
from database import get_session, Business, ProcessingLog
import phonenumbers
from phonenumbers import NumberParseException
import usaddress
from datetime import datetime

class DataNormalizer:
    """Main class for normalizing and deduplicating business data"""
    
    def __init__(self):
        self.session = get_session()
        
        # Common business suffixes and their normalized forms
        self.business_suffixes = {
            'ltd': 'ltd', 'limited': 'ltd', 'ltd.': 'ltd',
            'inc': 'inc', 'incorporated': 'inc', 'inc.': 'inc',
            'corp': 'corp', 'corporation': 'corp', 'corp.': 'corp',
            'llc': 'llc', 'l.l.c.': 'llc', 'l.l.c': 'llc',
            'co': 'co', 'company': 'co', 'co.': 'co',
            'restaurant': 'restaurant', 'rest': 'restaurant',
            'cafe': 'cafe', 'coffee': 'cafe',
            'pizza': 'pizza', 'pizzeria': 'pizza',
            'takeaway': 'takeaway', 'take-away': 'takeaway',
            'bakery': 'bakery', 'baker': 'bakery',
            'pub': 'pub', 'public house': 'pub',
            'bar': 'bar', 'tavern': 'bar'
        }
        
        # Common words to remove from business names
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'under'
        }
        
        # Aggregator domains to filter out
        self.aggregator_domains = {
            'yelp.com', 'tripadvisor.com', 'justeat.co.uk', 'deliveroo.co.uk',
            'ubereats.com', 'grubhub.com', 'opentable.com', 'zomato.com',
            'foursquare.com', 'google.com', 'facebook.com', 'instagram.com'
        }
    
    def normalize_business_name(self, name: str) -> str:
        """
        Normalize business name by removing common variations and standardizing format
        
        Args:
            name: Raw business name
            
        Returns:
            Normalized business name
        """
        if not name:
            return ""
        
        # Convert to lowercase
        normalized = name.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common punctuation
        normalized = normalized.translate(str.maketrans('', '', string.punctuation))
        
        # Remove stop words
        words = normalized.split()
        words = [word for word in words if word not in self.stop_words]
        
        # Normalize business suffixes
        for i, word in enumerate(words):
            if word in self.business_suffixes:
                words[i] = self.business_suffixes[word]
        
        return ' '.join(words)
    
    def normalize_address(self, address: str) -> str:
        """
        Normalize address by standardizing format and abbreviations
        
        Args:
            address: Raw address string
            
        Returns:
            Normalized address
        """
        if not address:
            return ""
        
        # Convert to lowercase
        normalized = address.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Standardize common abbreviations
        abbreviations = {
            'st.': 'street', 'street': 'street',
            'ave.': 'avenue', 'avenue': 'avenue',
            'rd.': 'road', 'road': 'road',
            'dr.': 'drive', 'drive': 'drive',
            'ln.': 'lane', 'lane': 'lane',
            'ct.': 'court', 'court': 'court',
            'pl.': 'place', 'place': 'place',
            'blvd.': 'boulevard', 'boulevard': 'boulevard',
            'apt.': 'apartment', 'apartment': 'apartment',
            'ste.': 'suite', 'suite': 'suite',
            'unit': 'unit', 'u.': 'unit'
        }
        
        for abbr, full in abbreviations.items():
            normalized = re.sub(r'\b' + re.escape(abbr) + r'\b', full, normalized)
        
        return normalized
    
    def normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number to international format
        
        Args:
            phone: Raw phone number string
            
        Returns:
            Normalized phone number or empty string if invalid
        """
        if not phone:
            return ""
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        try:
            # Parse phone number (assuming UK if no country code)
            if not cleaned.startswith('+'):
                cleaned = '+44' + cleaned.lstrip('0')
            
            parsed = phonenumbers.parse(cleaned, None)
            
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            else:
                return ""
                
        except NumberParseException:
            return ""
    
    def calculate_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two business names
        
        Args:
            name1: First business name
            name2: Second business name
            
        Returns:
            Similarity score between 0 and 1
        """
        if not name1 or not name2:
            return 0.0
        
        # Normalize both names
        norm1 = self.normalize_business_name(name1)
        norm2 = self.normalize_business_name(name2)
        
        # Use SequenceMatcher for similarity
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Boost similarity if one name contains the other
        if norm1 in norm2 or norm2 in norm1:
            similarity = max(similarity, 0.8)
        
        return similarity
    
    def find_duplicates(self, threshold: float = 0.8) -> List[List[int]]:
        """
        Find duplicate businesses based on name and address similarity
        
        Args:
            threshold: Similarity threshold for considering businesses as duplicates
            
        Returns:
            List of duplicate groups (each group contains business IDs)
        """
        logger.info(f"Starting duplicate detection with threshold {threshold}")
        
        # Get all businesses
        businesses = self.session.query(Business).all()
        logger.info(f"Checking {len(businesses)} businesses for duplicates")
        
        duplicate_groups = []
        processed = set()
        
        for i, business1 in enumerate(businesses):
            if business1.id in processed:
                continue
            
            current_group = [business1.id]
            processed.add(business1.id)
            
            for j, business2 in enumerate(businesses[i+1:], i+1):
                if business2.id in processed:
                    continue
                
                # Calculate name similarity
                name_similarity = self.calculate_similarity(business1.name, business2.name)
                
                # Calculate address similarity
                address_similarity = 0.0
                if business1.address and business2.address:
                    address_similarity = self.calculate_similarity(
                        business1.address, business2.address
                    )
                
                # Consider as duplicate if name similarity is high and addresses are similar
                if (name_similarity >= threshold and 
                    (address_similarity >= 0.5 or not business1.address or not business2.address)):
                    
                    current_group.append(business2.id)
                    processed.add(business2.id)
                    
                    logger.info(f"Found potential duplicate: {business1.name} <-> {business2.name}")
            
            if len(current_group) > 1:
                duplicate_groups.append(current_group)
        
        logger.info(f"Found {len(duplicate_groups)} duplicate groups")
        return duplicate_groups
    
    def merge_duplicates(self, duplicate_groups: List[List[int]]) -> int:
        """
        Merge duplicate businesses, keeping the one with most complete data
        
        Args:
            duplicate_groups: List of duplicate groups to merge
            
        Returns:
            Number of businesses merged
        """
        merged_count = 0
        
        for group in duplicate_groups:
            if len(group) < 2:
                continue
            
            # Get all businesses in the group
            businesses = self.session.query(Business).filter(Business.id.in_(group)).all()
            
            # Find the best business to keep (most complete data)
            best_business = self._select_best_business(businesses)
            businesses_to_merge = [b for b in businesses if b.id != best_business.id]
            
            # Merge data from other businesses
            for business in businesses_to_merge:
                self._merge_business_data(best_business, business)
                self.session.delete(business)
                merged_count += 1
            
            # Log the merge
            self._log_processing(
                business_id=best_business.id,
                process_type="merge_duplicates",
                status="success",
                message=f"Merged {len(businesses_to_merge)} duplicates into business {best_business.name}"
            )
        
        self.session.commit()
        logger.info(f"Merged {merged_count} duplicate businesses")
        return merged_count
    
    def _select_best_business(self, businesses: List[Business]) -> Business:
        """Select the best business to keep from a group of duplicates"""
        best_score = -1
        best_business = businesses[0]
        
        for business in businesses:
            score = 0
            
            # Score based on data completeness
            if business.name:
                score += 1
            if business.address:
                score += 1
            if business.phone:
                score += 1
            if business.website_url:
                score += 1
            if business.social_links:
                score += 1
            
            # Prefer businesses with more sources
            if business.sources:
                score += len(business.sources)
            
            if score > best_score:
                best_score = score
                best_business = business
        
        return best_business
    
    def _merge_business_data(self, target: Business, source: Business):
        """Merge data from source business into target business"""
        # Merge sources
        if source.sources:
            if target.sources:
                target.sources = list(set(target.sources + source.sources))
            else:
                target.sources = source.sources
        
        # Fill in missing data
        if not target.phone and source.phone:
            target.phone = source.phone
        
        if not target.address and source.address:
            target.address = source.address
        
        if not target.city and source.city:
            target.city = source.city
        
        if not target.postcode and source.postcode:
            target.postcode = source.postcode
        
        if not target.website_url and source.website_url:
            target.website_url = source.website_url
        
        if not target.social_links and source.social_links:
            target.social_links = source.social_links
        
        # Update timestamp
        target.updated_at = datetime.utcnow()
    
    def normalize_all_businesses(self) -> int:
        """
        Normalize all business data in the database
        
        Returns:
            Number of businesses processed
        """
        logger.info("Starting normalization of all businesses")
        
        businesses = self.session.query(Business).all()
        processed_count = 0
        
        for business in businesses:
            try:
                # Normalize name
                if business.name:
                    business.normalized_name = self.normalize_business_name(business.name)
                
                # Normalize address
                if business.address:
                    business.normalized_address = self.normalize_address(business.address)
                
                # Normalize phone
                if business.phone:
                    normalized_phone = self.normalize_phone(business.phone)
                    if normalized_phone:
                        business.phone = normalized_phone
                
                processed_count += 1
                
                # Log progress
                if processed_count % 100 == 0:
                    logger.info(f"Processed {processed_count} businesses")
                
            except Exception as e:
                logger.error(f"Error normalizing business {business.id}: {e}")
                self._log_processing(
                    business_id=business.id,
                    process_type="normalize",
                    status="error",
                    message=f"Error normalizing business: {str(e)}"
                )
        
        self.session.commit()
        logger.info(f"Successfully normalized {processed_count} businesses")
        return processed_count
    
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
    
    def close(self):
        """Close database session"""
        self.session.close()

# Example usage and testing
if __name__ == "__main__":
    normalizer = DataNormalizer()
    
    # Normalize all businesses
    # normalizer.normalize_all_businesses()
    
    # Find and merge duplicates
    # duplicates = normalizer.find_duplicates(threshold=0.8)
    # normalizer.merge_duplicates(duplicates)
    
    normalizer.close()
