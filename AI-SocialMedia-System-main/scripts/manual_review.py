from database import BusinessStatus, get_db_session, Business
from loguru import logger
from tabulate import tabulate
import sys

def print_business_info(business):
    """Print detailed information about a business."""
    print("\n" + "="*80)
    print(f"Business ID: {business.id}")
    print(f"Name: {business.name}")
    print(f"Address: {business.address}")
    print(f"Website Present: {business.website_present}")
    print(f"Website URL: {business.website_url}")
    print(f"Social Present: {business.social_present}")
    print(f"Social Links: {business.social_links}")
    print(f"Current Status: {business.status}")
    print(f"Confidence Score: {business.confidence_score}")
    print(f"Google Rating: {business.google_rating}")
    print(f"Google Review Count: {business.google_review_count}")
    print("="*80)

def manual_review():
    """Allow manual review of business classifications."""
    session = get_db_session()
    
    while True:
        print("\nManual Review Options:")
        print("1. Review rejected businesses")
        print("2. Review approved businesses")
        print("3. Review all businesses")
        print("4. Show statistics")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ")
        
        if choice == "5":
            break
            
        if choice == "4":
            # Get statistics
            total = session.query(Business).count()
            approved = session.query(Business).filter(Business.status == BusinessStatus.APPROVED).count()
            rejected = session.query(Business).filter(Business.status == BusinessStatus.REJECTED).count()
            pending = session.query(Business).filter(Business.status == BusinessStatus.PENDING).count()
            
            stats = [
                ["Total", total],
                ["Approved", approved],
                ["Rejected", rejected],
                ["Pending", pending]
            ]
            print("\nClassification Statistics:")
            print(tabulate(stats, headers=["Category", "Count"], tablefmt="grid"))
            continue
            
        # Get businesses based on choice
        if choice == "1":
            businesses = session.query(Business).filter(Business.status == BusinessStatus.REJECTED).all()
            category = "rejected"
        elif choice == "2":
            businesses = session.query(Business).filter(Business.status == BusinessStatus.APPROVED).all()
            category = "approved"
        elif choice == "3":
            businesses = session.query(Business).all()
            category = "all"
        else:
            print("Invalid choice. Please try again.")
            continue
            
        if not businesses:
            print(f"\nNo {category} businesses found.")
            continue
            
        print(f"\nReviewing {category} businesses...")
        
        for business in businesses:
            print_business_info(business)
            
            while True:
                action = input("\nActions:\n"
                             "a - Mark as Approved\n"
                             "r - Mark as Rejected\n"
                             "p - Mark as Pending\n"
                             "s - Skip to next business\n"
                             "q - Quit review\n"
                             "Choice: ").lower()
                
                if action == 'q':
                    session.commit()
                    return
                elif action == 's':
                    break
                elif action in ['a', 'r', 'p']:
                    if action == 'a':
                        business.status = BusinessStatus.APPROVED
                        print("Marked as APPROVED")
                    elif action == 'r':
                        business.status = BusinessStatus.REJECTED
                        print("Marked as REJECTED")
                    else:
                        business.status = BusinessStatus.PENDING
                        print("Marked as PENDING")
                    session.commit()
                    break
                else:
                    print("Invalid choice. Please try again.")
        
        print(f"\nFinished reviewing {category} businesses.")
    
    session.close()
    print("\nManual review completed.")

if __name__ == "__main__":
    try:
        manual_review()
    except KeyboardInterrupt:
        print("\nManual review interrupted.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error during manual review: {e}")
        sys.exit(1)