"""
Website detection module for the Business Finder system.
Checks for business websites using Google search and filters out aggregator sites.
"""

import requests
import re
import time
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright not installed. Some features will be disabled.")
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from loguru import logger
from database import SessionLocal, Business, ProcessingLog

def get_session():
    return SessionLocal()
from dotenv import load_dotenv
import googlemaps
from playwright.sync_api import sync_playwright

load_dotenv()

class WebsiteChecker:
    """Main class for detecting business websites"""
    
    def __init__(self):
        self.session = get_session()
        self.gmaps = None
        self._init_google_maps()
        
        # Domains that indicate digital presence
        self.digital_presence_domains = {
            # Review and Directory Sites
            'yelp.com', 'tripadvisor.com', 'zomato.com', 'foursquare.com',
            'theculturetrip.com', 'timeout.com', 'eater.com', 'infatuation.com',
            
            # Delivery Platforms
            'ubereats.com', 'glovo.com', 'deliveroo.com', 'justeat.com',
            'grubhub.com', 'doordash.com', 'thuisbezorgd.nl',
            
            # Booking Platforms
            'opentable.com', 'thefork.com', 'resy.com', 'bookatable.com',
            
            # Social Media
            'facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com',
            'pinterest.com', 'tiktok.com', 'youtube.com',
            
            # Google Properties
            'google.com', 'googlemaps.com', 'google.pt', 'google.maps.com',
            'business.site', 'restaurants.google.com',
            
            # Messaging/Chat
            'whatsapp.com', 'telegram.org', 'messenger.com',
            
            # Local Portugal Sites
            'zomato.pt', 'nit.pt', 'timeout.pt', 'lisboacool.com',
            'foodbloggerspt.com', 'gostar.pt', 'cityguidelisbon.com',
            
            # Booking/Reservation
            'reservar.pt', 'mesa247.pt', 'bookatable.pt', 'zomato.pt/booking'
        }
        
        # User agent for web requests
        self.user_agent = os.getenv("USER_AGENT", 
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        # Request delay to avoid rate limiting
        self.request_delay = float(os.getenv("REQUEST_DELAY", "1.0"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
    
    def _init_google_maps(self):
        """Initialize Google Maps client if API key is available"""
        api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if api_key and api_key != "your_google_places_api_key_here":
            self.gmaps = googlemaps.Client(key=api_key)
            logger.info("Google Maps client initialized")
        else:
            logger.warning("Google Places API key not found. Google Places search will be disabled.")
    
    def check_business_website(self, business: Business) -> Tuple[bool, Optional[str]]:
        """
        Check if a business has a website
        
        Args:
            business: Business object to check
            
        Returns:
            Tuple of (has_website, website_url)
        """
        logger.info(f"Checking website for business: {business.name}")
        
        # First check if we already have a website from API data
        if business.website_url and not self._is_aggregator_domain(business.website_url):
            logger.info(f"Found website from API data: {business.website_url}")
            return True, business.website_url
        
        # Search for website using Google search
        search_results = self._search_google(business.name, business.city)
        
        if not search_results:
            logger.info(f"No search results found for {business.name}")
            return False, None
        
        # Filter out aggregator sites and find the best website
        best_website = self._find_best_website(search_results, business.name)
        
        if best_website:
            logger.info(f"Found website: {best_website}")
            return True, best_website
        else:
            logger.info(f"No valid website found for {business.name}")
            return False, None
    
    def _search_google(self, business_name: str, city: str = None) -> List[Dict]:
        """
        Search Google for business website
        
        Args:
            business_name: Name of the business
            city: City where business is located
            
        Returns:
            List of search results
        """
        if not self.gmaps:
            logger.warning("Google Maps client not available, using web search")
            return self._search_google_web(business_name, city)
        
        try:
            # Use Google Places API for more accurate results
            query = f"{business_name}"
            if city:
                query += f" {city}"
            
            places_result = self.gmaps.places(query=query, type='establishment')
            
            results = []
            for place in places_result.get('results', []):
                if place.get('website'):
                    results.append({
                        'title': place.get('name', ''),
                        'url': place.get('website', ''),
                        'snippet': place.get('formatted_address', ''),
                        'source': 'google_places'
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching Google Places: {e}")
            return self._search_google_web(business_name, city)
    
    def _search_google_web(self, business_name: str, city: str = None) -> List[Dict]:
        """
        Search Google using web scraping (fallback method)
        
        Args:
            business_name: Name of the business
            city: City where business is located
            
        Returns:
            List of search results
        """
        try:
            # Build search query
            query = f'"{business_name}"'
            if city:
                query += f' "{city}"'
            query += ' website'
            
            # Use Playwright for more reliable scraping
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_extra_http_headers({"User-Agent": self.user_agent})
                
                # Navigate to Google search
                search_url = f"https://www.google.com/search?q={query}"
                page.goto(search_url)
                
                # Wait for results to load
                page.wait_for_timeout(2000)
                
                # Extract search results
                results = []
                search_results = page.query_selector_all('div[data-ved]')
                
                for result in search_results[:5]:  # Limit to first 5 results
                    try:
                        title_element = result.query_selector('h3')
                        link_element = result.query_selector('a')
                        snippet_element = result.query_selector('span')
                        
                        if title_element and link_element:
                            title = title_element.inner_text()
                            url = link_element.get_attribute('href')
                            snippet = snippet_element.inner_text() if snippet_element else ''
                            
                            if url and url.startswith('http'):
                                results.append({
                                    'title': title,
                                    'url': url,
                                    'snippet': snippet,
                                    'source': 'google_web'
                                })
                    except Exception as e:
                        logger.debug(f"Error parsing search result: {e}")
                        continue
                
                browser.close()
                return results
                
        except Exception as e:
            logger.error(f"Error in Google web search: {e}")
            return []
    
    def _has_digital_presence(self, url: str, content: Optional[str] = None) -> Dict:
        """
        Check if a URL or content indicates digital presence
        
        Args:
            url: URL to check
            content: Optional HTML content to check
            
        Returns:
            Dictionary with digital presence details
        """
        result = {
            'has_presence': False,
            'type': [],
            'details': []
        }
        
        if not url:
            return result
        
        try:
            domain = urlparse(url).netloc.lower()
            domain = domain.replace('www.', '')
            
            # Check if domain matches any known digital presence platforms
            for known_domain in self.digital_presence_domains:
                if known_domain in domain:
                    result['has_presence'] = True
                    if 'google' in domain:
                        result['type'].append('google_maps')
                        result['details'].append('Has Google Maps presence')
                    elif any(social in domain for social in ['facebook', 'instagram', 'twitter', 'tiktok']):
                        result['type'].append('social_media')
                        result['details'].append(f'Has profile on {domain}')
                    elif any(delivery in domain for delivery in ['ubereats', 'glovo', 'deliveroo']):
                        result['type'].append('delivery_platform')
                        result['details'].append(f'Available on {domain}')
                    elif any(blog in domain for blog in ['timeout', 'nit.pt', 'lisboacool']):
                        result['type'].append('food_blog')
                        result['details'].append(f'Featured on {domain}')
                    break
            
            # Check content for indicators of digital presence
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                
                # Check for social media links
                social_links = soup.find_all('a', href=re.compile(r'(facebook|instagram|twitter)'))
                if social_links:
                    result['has_presence'] = True
                    result['type'].append('social_media')
                    result['details'].append('Has social media links on website')
                
                # Check for Google Maps embed
                if soup.find_all('iframe', src=re.compile(r'google.com/maps')):
                    result['has_presence'] = True
                    result['type'].append('google_maps')
                    result['details'].append('Has embedded Google Maps')
                
                # Check for online ordering systems
                if soup.find_all(text=re.compile(r'(order online|delivery|takeaway|uber eats|glovo)')):
                    result['has_presence'] = True
                    result['type'].append('online_ordering')
                    result['details'].append('Offers online ordering')
            
            return result
            
        except Exception as e:
            logger.debug(f"Error parsing URL {url}: {e}")
            return False
    
    def _find_best_website(self, search_results: List[Dict], business_name: str) -> Optional[str]:
        """
        Find the best website from search results
        
        Args:
            search_results: List of search results
            business_name: Name of the business
            
        Returns:
            Best website URL or None
        """
        if not search_results:
            return None
        
        # Score each result
        scored_results = []
        
        for result in search_results:
            url = result.get('url', '')
            title = result.get('title', '').lower()
            snippet = result.get('snippet', '').lower()
            
            # Skip aggregator sites
            if self._is_aggregator_domain(url):
                continue
            
            score = 0
            
            # Score based on title similarity to business name
            business_name_lower = business_name.lower()
            if business_name_lower in title:
                score += 3
            
            # Score based on snippet content
            if business_name_lower in snippet:
                score += 2
            
            # Prefer HTTPS
            if url.startswith('https://'):
                score += 1
            
            # Prefer shorter URLs (likely main domain)
            if len(url) < 50:
                score += 1
            
            # Prefer URLs with business name in domain
            domain = urlparse(url).netloc.lower()
            if business_name_lower.replace(' ', '') in domain:
                score += 2
            
            scored_results.append((score, url))
        
        if not scored_results:
            return None
        
        # Return the highest scoring result
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return scored_results[0][1]
    
    def verify_website(self, url: str) -> bool:
        """
        Verify that a website is accessible and appears to be a business website
        
        Args:
            url: URL to verify
            
        Returns:
            True if website is valid and accessible
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
            
            # Check if it's a valid business website
            return self._is_business_website(response.text, url)
            
        except Exception as e:
            logger.debug(f"Error verifying website {url}: {e}")
            return False
    
    def _is_business_website(self, html_content: str, url: str) -> bool:
        """
        Check if HTML content appears to be a business website
        
        Args:
            html_content: HTML content of the page
            url: URL of the page
            
        Returns:
            True if it appears to be a business website
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Check for business indicators
            business_indicators = [
                'contact', 'about', 'menu', 'hours', 'location', 'address',
                'phone', 'email', 'booking', 'reservation', 'order', 'delivery'
            ]
            
            text_content = soup.get_text().lower()
            
            # Count business indicators
            indicator_count = sum(1 for indicator in business_indicators 
                                if indicator in text_content)
            
            # Check for social media links (good sign for business)
            social_links = soup.find_all('a', href=re.compile(r'(facebook|instagram|twitter|linkedin)'))
            
            # Check for contact information
            contact_info = soup.find_all(text=re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'))
            
            # Score the website
            score = 0
            
            if indicator_count >= 3:
                score += 2
            elif indicator_count >= 1:
                score += 1
            
            if social_links:
                score += 1
            
            if contact_info:
                score += 1
            
            # Check if it's not a generic page
            if len(text_content) > 500:  # Substantial content
                score += 1
            
            return score >= 2
            
        except Exception as e:
            logger.debug(f"Error analyzing website content: {e}")
            return False
    
    def check_all_businesses(self) -> int:
        """
        Check websites for all businesses in the database
        
        Returns:
            Number of businesses processed
        """
        logger.info("Starting website check for all businesses")
        
        businesses = self.session.query(Business).all()
        processed_count = 0
        
        for business in businesses:
            try:
                # Skip if already checked recently
                if (business.website_present is not None and 
                    business.last_checked_date and 
                    (datetime.utcnow() - business.last_checked_date).days < 7):
                    continue
                
                # Check for website
                has_website, website_url = self.check_business_website(business)
                
                # Update business record
                business.website_present = has_website
                business.website_url = website_url
                business.last_checked_date = datetime.utcnow()
                
                processed_count += 1
                
                # Log progress
                if processed_count % 10 == 0:
                    logger.info(f"Processed {processed_count} businesses")
                
                # Log the result
                self._log_processing(
                    business_id=business.id,
                    process_type="website_check",
                    status="success",
                    message=f"Website check completed: {has_website}",
                    details={"website_url": website_url}
                )
                
            except Exception as e:
                logger.error(f"Error checking website for business {business.id}: {e}")
                self._log_processing(
                    business_id=business.id,
                    process_type="website_check",
                    status="error",
                    message=f"Error checking website: {str(e)}"
                )
        
        self.session.commit()
        logger.info(f"Successfully checked websites for {processed_count} businesses")
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
    checker = WebsiteChecker()
    
    # Check websites for all businesses
    # checker.check_all_businesses()
    
    # Check specific business
    # business = checker.session.query(Business).first()
    # if business:
    #     has_website, url = checker.check_business_website(business)
    #     print(f"Business: {business.name}, Website: {has_website}, URL: {url}")
    
    checker.close()
