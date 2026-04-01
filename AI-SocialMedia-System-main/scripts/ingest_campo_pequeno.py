from ingest import DataIngester

# Campo Pequeno, Lisboa bounding box coordinates
# Approximate area around Campo Pequeno
CAMPO_PEQUENO_BBOX = (
    38.7415,  # min_lat
    -9.1505,  # min_lon
    38.7455,  # max_lat
    -9.1445   # max_lon
)

def main():
    ingester = DataIngester()
    
    try:
        print("Starting data ingestion for Campo Pequeno area...")
        
        # Business types to search for
        business_types = [
            'restaurant',
            'cafe',
            'fast_food',
            'bar',
            'pub',
            'bakery'
        ]
        
        # Ingest from OpenStreetMap
        businesses = ingester.ingest_osm(
            bbox=CAMPO_PEQUENO_BBOX,
            business_types=business_types
        )
        
        print(f"Successfully ingested {len(businesses)} businesses")
        
        # Print the businesses found
        for business in businesses:
            print(f"\nName: {business['name']}")
            print(f"Address: {business['address']}")
            if business.get('phone'):
                print(f"Phone: {business['phone']}")
    
    except Exception as e:
        print(f"Error during ingestion: {e}")
    
    finally:
        ingester.close()

if __name__ == "__main__":
    main()