import requests
import json

# Test if server is running
try:
    response = requests.get("http://localhost:8000/api/downloads")
    print(f"API Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error connecting to API: {e}")

# Test adding a download
try:
    test_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    response = requests.post(
        "http://localhost:8000/api/download",
        json={"url": test_url}
    )
    print(f"\nAdd Download Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error adding download: {e}")
