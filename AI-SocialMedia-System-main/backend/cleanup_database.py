"""
Cleanup script to remove restaurants with significant digital presence
"""
from database import SessionLocal, Business
from datetime import datetime

def is_franchise(name: str) -> bool:
    """Check if business is a franchise/chain"""
    franchise_indicators = [
        'Burger King', 'McDonald', 'KFC', 'Pizza Hut', 'Domino',
        'Starbucks', 'Subway', 'Taco Bell', '100 Montaditos',
        'h3', 'TGB', 'Wok to Walk', 'Granier'
    ]
    
    return any(franchise.lower() in name.lower() for franchise in franchise_indicators)

def cleanup_database():
    """Remove restaurants that don't meet our criteria for lacking digital presence"""
    session = SessionLocal()
    total_removed = 0
    
    try:
        print("Starting database cleanup...")
        
        # Get all businesses
        businesses = session.query(Business).all()
        
        for business in businesses:
            should_remove = False
            reason = []
            
            # Check if it's a franchise
            if is_franchise(business.name):
                should_remove = True
                reason.append("franchise/chain")
            
            # Check delivery platforms and blog mentions
            if business.delivery_platforms or business.blog_mentions:
                should_remove = True
                if business.delivery_platforms:
                    reason.append("on delivery platforms")
                if business.blog_mentions:
                    reason.append("mentioned in blogs")
            
            # Check social media presence
            if business.social_present:
                should_remove = True
                reason.append("active on social media")
            
            # Check Google Maps presence with photos
            if business.google_maps_photos:
                should_remove = True
                reason.append("active Google Maps presence")
            
            # Check online ordering
            if business.online_ordering:
                should_remove = True
                reason.append("offers online ordering")
            
            # Remove if any criteria met
            if should_remove:
                print(f"Removing {business.name} - Reason: {', '.join(reason)}")
                session.delete(business)
                total_removed += 1
        
        # Commit changes
        session.commit()
        
        # Print summary
        remaining = session.query(Business).count()
        print(f"\nCleanup complete:")
        print(f"- Removed {total_removed} businesses")
        print(f"- Remaining businesses: {remaining}")
        
        # Print remaining businesses
        print("\nRemaining businesses (potential targets):")
        for business in session.query(Business).all():
            print(f"\nName: {business.name}")
            print(f"Address: {business.address or 'Not available'}")
            if business.phone:
                print(f"Phone: {business.phone}")
            if business.notes:
                print(f"Notes: {business.notes}")
    
    except Exception as e:
        print(f"Error during cleanup: {e}")
        session.rollback()
    
    finally:
        session.close()

if __name__ == "__main__":
    cleanup_database()