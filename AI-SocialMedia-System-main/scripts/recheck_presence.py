from database import SessionLocal, Business
from website_checker import WebsiteChecker
from datetime import datetime
import json

def recheck_digital_presence():
    """
    Recheck all businesses with stricter digital presence criteria
    """
    session = SessionLocal()
    checker = WebsiteChecker()
    
    try:
        print("Starting strict digital presence check...")
        businesses = session.query(Business).all()
        
        for business in businesses:
            print(f"\nChecking {business.name}...")
            
            # Reset digital presence fields
            business.website_present = False
            business.social_present = False
            business.google_maps_photos = False
            business.delivery_platforms = None
            business.blog_mentions = None
            business.online_ordering = False
            business.digital_presence_details = None
            
            # Check for website and digital presence
            if business.website_url:
                presence_check = checker._has_digital_presence(business.website_url)
                if presence_check['has_presence']:
                    business.digital_presence_details = presence_check
                    
                    # Update specific fields based on findings
                    if 'social_media' in presence_check['type']:
                        business.social_present = True
                    if 'google_maps' in presence_check['type']:
                        business.google_maps_photos = True
                    if 'delivery_platform' in presence_check['type']:
                        business.online_ordering = True
                    if 'food_blog' in presence_check['type']:
                        business.blog_mentions = json.dumps(presence_check['details'])
                    
                    print("Digital presence found:")
                    print(json.dumps(presence_check, indent=2))
                else:
                    print("No significant digital presence detected")
            
            business.last_checked_date = datetime.utcnow()
        
        # Commit changes
        session.commit()
        print("\nFinished digital presence recheck")
        
    except Exception as e:
        print(f"Error during recheck: {e}")
        session.rollback()
    
    finally:
        session.close()
        checker.close()

if __name__ == "__main__":
    recheck_digital_presence()