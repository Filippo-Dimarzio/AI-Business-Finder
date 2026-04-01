"""
Social media detection module for the Business Finder system.
Searches for business social media presence on Facebook, Instagram, Twitter/X, and LinkedIn.
"""

import requests
import re
import time
import os
import json
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup
from loguru import logger
from database import SessionLocal, Business, ProcessingLog
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from datetime import datetime

load_dotenv()

class SocialMediaChecker:
    """Main class for detecting business social media presence"""
    
    def __init__(self):
        self.session = SessionLocal()
        
        # Social media platforms to check
        self.platforms = {
            'facebook': {
                'base_url': 'https://www.facebook.com',
                'search_url': 'https://www.facebook.com/search/pages/?q=',
                'pattern': r'facebook\.com/[^/]+/?$'
            },
            'instagram': {
                'base_url': 'https://www.instagram.com',
                'search_url': 'https://www.instagram.com/explore/tags/',
                'pattern': r'instagram\.com/[^/]+/?$'
            },
            'twitter': {
                'base_url': 'https://twitter.com',
                'search_url': 'https://twitter.com/search?q=',
                'pattern': r'twitter\.com/[^/]+/?$'
            },
            'linkedin': {
                'base_url': 'https://www.linkedin.com',
                'search_url': 'https://www.linkedin.com/search/results/companies/?keywords=',
                'pattern': r'linkedin\.com/company/[^/]+/?$'
            }
        }
        
        # User agent for web requests
        self.user_agent = os.getenv("USER_AGENT", 
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        # Request delay to avoid rate limiting
        self.request_delay = float(os.getenv("REQUEST_DELAY", "2.0"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
    
    def check_business_social_media(self, business: Business) -> Tuple[bool, Dict[str, str]]:
        """
        Check if a business has social media presence
        
        Args:
            business: Business object to check
            
        Returns:
            Tuple of (has_social_media, social_links_dict)
        """
        logger.info(f"Checking social media for business: {business.name}")
        
        social_links = {}
        has_social_media = False
        
        # Check each platform
        for platform, config in self.platforms.items():
            try:
                link = self._search_platform(business, platform, config)
                if link:
                    social_links[platform] = link
                    has_social_media = True
                    logger.info(f"Found {platform} profile: {link}")
                
                # Add delay between requests
                time.sleep(self.request_delay)
                
            except Exception as e:
                logger.error(f"Error checking {platform} for {business.name}: {e}")
                self._log_processing(
                    business_id=business.id,
                    process_type="social_media_check",
                    status="error",
                    message=f"Error checking {platform}: {str(e)}"
                )
        
        return has_social_media, social_links
    
    def _search_platform(self, business: Business, platform: str, config: Dict) -> Optional[str]:
        """
        Search for business on a specific social media platform
        
        Args:
            business: Business object
            platform: Platform name
            config: Platform configuration
            
        Returns:
            Social media URL if found, None otherwise
        """
        try:
            # Build search query
            query = f'"{business.name}"'
            if business.city:
                query += f' "{business.city}"'
            
            # Use Playwright for more reliable scraping
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_extra_http_headers({"User-Agent": self.user_agent})
                
                # Navigate to search page
                search_url = config['search_url'] + quote_plus(query)
                page.goto(search_url)
                
                # Wait for results to load
                page.wait_for_timeout(3000)
                
                # Look for business profile
                profile_link = self._find_business_profile(page, business, platform, config)
                
                browser.close()
                return profile_link
                
        except Exception as e:
            logger.error(f"Error searching {platform}: {e}")
            return None
    
    def _find_business_profile(self, page, business: Business, platform: str, config: Dict) -> Optional[str]:
        """
        Find business profile from search results page
        
        Args:
            page: Playwright page object
            business: Business object
            platform: Platform name
            config: Platform configuration
            
        Returns:
            Profile URL if found, None otherwise
        """
        try:
            # Platform-specific selectors and logic
            if platform == 'facebook':
                return self._find_facebook_profile(page, business)
            elif platform == 'instagram':
                return self._find_instagram_profile(page, business)
            elif platform == 'twitter':
                return self._find_twitter_profile(page, business)
            elif platform == 'linkedin':
                return self._find_linkedin_profile(page, business)
            
        except Exception as e:
            logger.error(f"Error finding {platform} profile: {e}")
            return None
    
    def _find_facebook_profile(self, page, business: Business) -> Optional[str]:
        """Find Facebook business page"""
        try:
            # Look for business pages in search results
            business_links = page.query_selector_all('a[href*="/pages/"]')
            
            for link in business_links:
                href = link.get_attribute('href')
                if href and 'facebook.com' in href:
                    # Check if this looks like the right business
                    title = link.inner_text().lower()
                    business_name_lower = business.name.lower()
                    
                    if business_name_lower in title or self._names_match(business.name, title):
                        return href
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding Facebook profile: {e}")
            return None
    
    def _find_instagram_profile(self, page, business: Business) -> Optional[str]:
        """Find Instagram business profile"""
        try:
            # Look for business profiles in search results
            profile_links = page.query_selector_all('a[href*="/"]')
            
            for link in profile_links:
                href = link.get_attribute('href')
                if href and 'instagram.com' in href and not href.endswith('/'):
                    # Check if this looks like the right business
                    title = link.inner_text().lower()
                    business_name_lower = business.name.lower()
                    
                    if business_name_lower in title or self._names_match(business.name, title):
                        return href
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding Instagram profile: {e}")
            return None
    
    def _find_twitter_profile(self, page, business: Business) -> Optional[str]:
        """Find Twitter business profile"""
        try:
            # Look for business profiles in search results
            profile_links = page.query_selector_all('a[href*="/"]')
            
            for link in profile_links:
                href = link.get_attribute('href')
                if href and 'twitter.com' in href and not href.endswith('/'):
                    # Check if this looks like the right business
                    title = link.inner_text().lower()
                    business_name_lower = business.name.lower()
                    
                    if business_name_lower in title or self._names_match(business.name, title):
                        return href
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding Twitter profile: {e}")
            return None
    
    def _find_linkedin_profile(self, page, business: Business) -> Optional[str]:
        """Find LinkedIn business page"""
        try:
            # Look for company pages in search results
            company_links = page.query_selector_all('a[href*="/company/"]')
            
            for link in company_links:
                href = link.get_attribute('href')
                if href and 'linkedin.com/company' in href:
                    # Check if this looks like the right business
                    title = link.inner_text().lower()
                    business_name_lower = business.name.lower()
                    
                    if business_name_lower in title or self._names_match(business.name, title):
                        return href
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding LinkedIn profile: {e}")
            return None
    
    def _names_match(self, business_name: str, profile_name: str) -> bool:
        """
        Check if business name matches profile name
        
        Args:
            business_name: Name of the business
            profile_name: Name from social media profile
            
        Returns:
            True if names match
        """
        if not business_name or not profile_name:
            return False
        
        # Normalize names
        business_normalized = re.sub(r'[^\w\s]', '', business_name.lower())
        profile_normalized = re.sub(r'[^\w\s]', '', profile_name.lower())
        
        # Check if business name is contained in profile name
        if business_normalized in profile_normalized:
            return True
        
        # Check if profile name is contained in business name
        if profile_normalized in business_normalized:
            return True
        
        # Check for common variations
        business_words = set(business_normalized.split())
        profile_words = set(profile_normalized.split())
        
        # If more than 50% of words match, consider it a match
        common_words = business_words.intersection(profile_words)
        if len(common_words) > 0 and len(common_words) / max(len(business_words), len(profile_words)) > 0.5:
            return True
        
        return False
    
    def verify_social_media_profile(self, url: str, platform: str) -> bool:
        """
        Verify that a social media profile is valid and accessible
        
        Args:
            url: Social media profile URL
            platform: Platform name
            
        Returns:
            True if profile is valid and accessible
        """
        if not url:
            return False
        
        try:
            # Add delay to avoid rate limiting
            time.sleep(self.request_delay)
            
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            response.raise_for_status()
            
            # Check if it's a valid profile page
            return self._is_valid_profile(response.text, platform)
            
        except Exception as e:
            logger.debug(f"Error verifying {platform} profile {url}: {e}")
            return False
    
    def _is_valid_profile(self, html_content: str, platform: str) -> bool:
        """
        Check if HTML content appears to be a valid social media profile
        
        Args:
            html_content: HTML content of the page
            platform: Platform name
            
        Returns:
            True if it appears to be a valid profile
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Platform-specific validation
            if platform == 'facebook':
                return self._is_valid_facebook_profile(soup)
            elif platform == 'instagram':
                return self._is_valid_instagram_profile(soup)
            elif platform == 'twitter':
                return self._is_valid_twitter_profile(soup)
            elif platform == 'linkedin':
                return self._is_valid_linkedin_profile(soup)
            
            return False
            
        except Exception as e:
            logger.debug(f"Error analyzing {platform} profile: {e}")
            return False
    
    def _is_valid_facebook_profile(self, soup: BeautifulSoup) -> bool:
        """Check if Facebook profile is valid"""
        # Look for Facebook-specific elements
        return (soup.find('meta', property='og:type', content='profile') is not None or
                soup.find('div', class_='profile') is not None or
                soup.find('div', id='pagelet_timeline_main_column') is not None)
    
    def _is_valid_instagram_profile(self, soup: BeautifulSoup) -> bool:
        """Check if Instagram profile is valid"""
        # Look for Instagram-specific elements
        return (soup.find('meta', property='og:type', content='profile') is not None or
                soup.find('div', class_='profile') is not None or
                soup.find('script', type='application/ld+json') is not None)
    
    def _is_valid_twitter_profile(self, soup: BeautifulSoup) -> bool:
        """Check if Twitter profile is valid"""
        # Look for Twitter-specific elements
        return (soup.find('meta', property='og:type', content='profile') is not None or
                soup.find('div', class_='profile') is not None or
                soup.find('div', class_='timeline') is not None)
    
    def _is_valid_linkedin_profile(self, soup: BeautifulSoup) -> bool:
        """Check if LinkedIn profile is valid"""
        # Look for LinkedIn-specific elements
        return (soup.find('meta', property='og:type', content='profile') is not None or
                soup.find('div', class_='profile') is not None or
                soup.find('div', class_='company-page') is not None)
    
    def check_all_businesses(self) -> int:
        """
        Check social media for all businesses in the database
        
        Returns:
            Number of businesses processed
        """
        logger.info("Starting social media check for all businesses")
        
        businesses = self.session.query(Business).all()
        processed_count = 0
        
        for business in businesses:
            try:
                # Skip if already checked recently
                if (business.social_present is not None and 
                    business.last_checked_date and 
                    (datetime.utcnow() - business.last_checked_date).days < 7):
                    continue
                
                # Check for social media
                has_social_media, social_links = self.check_business_social_media(business)
                
                # Update business record
                business.social_present = has_social_media
                business.social_links = social_links if social_links else None
                business.last_checked_date = datetime.utcnow()
                
                processed_count += 1
                
                # Log progress
                if processed_count % 5 == 0:  # Less frequent due to rate limiting
                    logger.info(f"Processed {processed_count} businesses")
                
                # Log the result
                self._log_processing(
                    business_id=business.id,
                    process_type="social_media_check",
                    status="success",
                    message=f"Social media check completed: {has_social_media}",
                    details={"social_links": social_links}
                )
                
            except Exception as e:
                logger.error(f"Error checking social media for business {business.id}: {e}")
                self._log_processing(
                    business_id=business.id,
                    process_type="social_media_check",
                    status="error",
                    message=f"Error checking social media: {str(e)}"
                )
        
        self.session.commit()
        logger.info(f"Successfully checked social media for {processed_count} businesses")
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
    checker = SocialMediaChecker()
    
    # Check social media for all businesses
    # checker.check_all_businesses()
    
    # Check specific business
    # business = checker.session.query(Business).first()
    # if business:
    #     has_social, links = checker.check_business_social_media(business)
    #     print(f"Business: {business.name}, Social: {has_social}, Links: {links}")
    
    checker.close()
