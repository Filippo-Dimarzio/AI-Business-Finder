import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_google_places_api():
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    print(f"Using API key: {api_key}")
    
    # Test with a Places Search request
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.id"
    }
    data = {
        "textQuery": "Restaurant in Lisbon"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        print("\nAPI Response:")
        print(result)
        
        if "places" in result:
            print("\nAPI key is working correctly!")
            return True
        else:
            print("\nAPI key verification failed")
            if "error" in result:
                print(f"Error message: {result.get('error', {}).get('message')}")
            return False
            
    except Exception as e:
        print(f"\nError testing API key: {e}")
        return False

if __name__ == "__main__":
    test_google_places_api()