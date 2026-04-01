from database import get_session, Business
from datetime import datetime

def add_sample_reviews():
    session = get_session()
    
    # Sample reviews data - mix of approved and rejected cases
    reviews = [
        # Known cases with no website/social media
        {"business_name": "Tasca do Chico", "review": "approved", "notes": "Confirmed local traditional tasca with no online presence"},
        {"business_name": "Café Central do Campo Pequeno", "review": "approved", "notes": "Traditional local café, verified no online presence"},
        {"business_name": "Pastelaria Alentejana", "review": "approved", "notes": "Old-school bakery, no digital presence"},
        {"business_name": "Churrasqueira Típica", "review": "approved", "notes": "Local grill, confirmed no website/social"},
        {"business_name": "Casa dos Bifes", "review": "approved", "notes": "Traditional steakhouse, no online channels"},
        
        # Cases with known digital presence
        {"business_name": "Burger King", "review": "rejected", "notes": "Has website and social media"},
        {"business_name": "Domino's", "review": "rejected", "notes": "Has website and delivery platforms"},
        {"business_name": "100 Montaditos", "review": "rejected", "notes": "Has social media presence"},
        {"business_name": "Portugália", "review": "rejected", "notes": "Has website and Instagram"},
        {"business_name": "Wok to Walk", "review": "rejected", "notes": "Has website and social channels"},
        
        # Additional cases for training variety
        {"business_name": "Taco Bell", "review": "rejected", "notes": "International chain with strong online presence"},
        {"business_name": "LAB a padaria portuguesa", "review": "rejected", "notes": "Modern bakery with digital presence"},
        {"business_name": "Sauvage", "review": "approved", "notes": "Small local business, no online presence"},
        {"business_name": "Picalho copo", "review": "approved", "notes": "Traditional bar, no digital channels"},
        {"business_name": "Pastelaria Granfina", "review": "approved", "notes": "Local pastry shop, no online presence"}
    ]
    
    for review_data in reviews:
        business = session.query(Business).filter(
            Business.name.like(f"%{review_data['business_name']}%")
        ).first()
        
        if business:
            business.human_review = review_data["review"]
            business.human_reviewer = "admin"
            business.human_review_date = datetime.utcnow()
            business.notes = review_data["notes"]
            print(f"Added review for {business.name}: {review_data['review']}")
    
    session.commit()
    session.close()
    print("Sample reviews added successfully")

if __name__ == "__main__":
    add_sample_reviews()
