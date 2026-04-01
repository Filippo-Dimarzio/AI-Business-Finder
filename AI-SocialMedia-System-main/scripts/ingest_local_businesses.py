from ingest import DataIngester
from database import SessionLocal, Business
from datetime import datetime

# Campo Pequeno and surrounding neighborhoods
LISBOA_AREAS = [
    {
        "name": "Campo Pequeno Area",
        "bbox": (38.7415, -9.1505, 38.7455, -9.1445)
    },
    {
        "name": "São Sebastião",
        "bbox": (38.7370, -9.1520, 38.7410, -9.1460)
    },
    {
        "name": "Entrecampos",
        "bbox": (38.7460, -9.1510, 38.7500, -9.1450)
    }
]

# Focus on traditional business types more likely to lack digital presence
TRADITIONAL_BUSINESS_TYPES = [
    'restaurant',      # Traditional restaurants
    'cafe',           # Local cafes
    'bar',            # Neighborhood bars
    'pub',            # Local pubs
    'food',           # Small food establishments
    'bakery',         # Traditional bakeries
    'confectionery',  # Sweet shops
    'deli',           # Delicatessens
    'fast_food'       # Local fast food places
]

def add_manual_businesses():
    """Add some manually verified local businesses"""
    session = SessionLocal()
    
    manual_businesses = [
        {
            "name": "Tasca do Chico",
            "address": "Rua Visconde de Seabra 2",
            "city": "Lisboa",
            "postcode": "1700-370",
            "sources": ["manual_entry"],
            "notes": "Traditional Portuguese tasca"
        },
        {
            "name": "Café Central do Campo Pequeno",
            "address": "Campo Pequeno",
            "city": "Lisboa",
            "sources": ["manual_entry"],
            "notes": "Traditional local café"
        },
        {
            "name": "Pastelaria Alentejana",
            "address": "Avenida da República",
            "city": "Lisboa",
            "sources": ["manual_entry"],
            "notes": "Traditional bakery"
        },
        {
            "name": "Churrasqueira Típica",
            "address": "Rua Actor Isidoro",
            "city": "Lisboa",
            "sources": ["manual_entry"],
            "notes": "Local grilled chicken restaurant"
        },
        {
            "name": "Casa dos Bifes",
            "address": "Avenida João XXI",
            "city": "Lisboa",
            "sources": ["manual_entry"],
            "notes": "Traditional steakhouse"
        }
    ]
    
    for business_data in manual_businesses:
        # Check if business already exists
        existing = session.query(Business).filter(
            Business.name == business_data["name"],
            Business.address == business_data["address"]
        ).first()
        
        if not existing:
            business = Business(
                **business_data,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(business)
    
    try:
        session.commit()
        print("Added manual business entries")
    except Exception as e:
        print(f"Error adding manual businesses: {e}")
        session.rollback()
    finally:
        session.close()

def main():
    ingester = DataIngester()
    
    try:
        print("Starting targeted data ingestion for traditional businesses...")
        
        # First, ingest from OpenStreetMap for each area
        total_ingested = 0
        for area in LISBOA_AREAS:
            print(f"\nProcessing {area['name']}...")
            businesses = ingester.ingest_osm(
                bbox=area['bbox'],
                business_types=TRADITIONAL_BUSINESS_TYPES
            )
            total_ingested += len(businesses)
        
        print(f"\nSuccessfully ingested {total_ingested} businesses from OSM")
        
        # Add manual entries of traditional businesses
        print("\nAdding manual entries of traditional businesses...")
        add_manual_businesses()
        
        # Print summary of businesses
        db = SessionLocal()
        total = db.query(Business).count()
        print(f"\nTotal businesses in database: {total}")
        
        # Print some examples
        print("\nSample businesses:")
        businesses = db.query(Business).limit(10).all()
        for business in businesses:
            print(f"\nName: {business.name}")
            print(f"Address: {business.address or 'Not available'}")
            print(f"Source: {', '.join(business.sources) if business.sources else 'Unknown'}")
            if business.notes:
                print(f"Notes: {business.notes}")
        
        db.close()
    
    except Exception as e:
        print(f"Error during ingestion: {e}")
    
    finally:
        ingester.close()

if __name__ == "__main__":
    main()