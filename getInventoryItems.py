import requests
import json
import config

# eBay Inventory API endpoint for getInventoryItems
EBAY_API_URL = "https://api.sandbox.ebay.com/sell/inventory/v1/inventory_item"

# Headers for the request
HEADERS = {
    "Authorization": f"Bearer {config.ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Query parameters
PARAMS = {
    "limit": 10,
    "offset": 0
}

# Make the API request
response = requests.get(EBAY_API_URL, headers=HEADERS, params=PARAMS)

# Parse the response
if response.status_code == 200:
    inventory_items = response.json()
    print(json.dumps(inventory_items, indent=4))
else:
    print("Error:", response.status_code, response.text)