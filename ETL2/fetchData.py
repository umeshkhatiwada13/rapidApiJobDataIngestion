import requests
import os
import json

# The endpoint for active ATS jobs
url = "https://active-jobs-db.p.rapidapi.com/active-ats"
# api_key = os.getenv("API_KEY")
api_key = "a17ef4656fmsh958f7fb30160c22p1b788fjsncdb8e2b8b6d4"

# Define your search filters
params = {"time_frame": "24h", "limit": "10"}

headers = {
    "x-rapidapi-key": api_key,
    "x-rapidapi-host": "active-jobs-db.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=params)

try:
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()  # Check for HTTP errors
    if response.status_code == 200:
        data = response.json()
        print(data)

        # Save the JSON data as a formatted text file
        with open("jsearch_response_2.json", "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

        print("Response successfully saved to jsearch_response.json")
    else:
        print(f"Request failed with status code {response.status_code}: {response.text}")

    jobs = response.json()
    for job in jobs:
        print(f"Title: {job.get('title')}")
        print(f"Company: {job.get('organization')}")
        print(f"Location: {job.get('location_raw')}")
        print(f"URL: {job.get('job_url')}")
        print("-" * 30)

except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
