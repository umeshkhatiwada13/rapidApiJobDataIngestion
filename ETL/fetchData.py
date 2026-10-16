import json
import requests
import os
from dotenv import load_dotenv

# 1. Load variables from the local .env file into environment variables
load_dotenv()

# 2. Access your variables securely using os.getenv()
API_KEY = os.getenv("API_KEY")
URL = os.getenv("FETCH_URL")

# URL and headers for fetching data
url = URL
headers = {
    "accept": "application/json",
    "x-rapidapi-host": "jsearch.p.rapidapi.com",
    "x-rapidapi-key": API_KEY
}
params = {
    "query": "Software Engineer",
    "country": "",
    "num_pages": ""
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    data = response.json()
    print(data)

    # Save the JSON data as a formatted text file
    with open("jsearch_response.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    print("Response successfully saved to jsearch_response.json")
else:
    print(f"Request failed with status code {response.status_code}: {response.text}")
