import requests
import json
import config

# eBay Finances API endpoint for getTransactions
EBAY_API_URL = "https://apiz.ebay.com/sell/finances/v1/transaction"

# Headers for the request
HEADERS = {
    "Authorization": f"Bearer {config.ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Query parameters
PARAMS = {
    "transaction_type": "ALL",
    "limit": 10,
    "offset": 0
}

# Make the API request
response = requests.get(EBAY_API_URL, headers=HEADERS, params=PARAMS)

# Parse the response
if response.status_code == 200:
    transactions = response.json()
    print(json.dumps(transactions, indent=4))
else:
    print("Error:", response.status_code, response.text)