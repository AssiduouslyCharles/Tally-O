import requests
import json

# eBay API credentials (replace with your own)
ACCESS_TOKEN = "v^1.1#i^1#r^0#p^3#f^0#I^3#t^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"

# eBay Finances API endpoint for getTransactions
EBAY_API_URL = "https://apiz.sandbox.ebay.com/sell/finances/v1/transaction"

# Headers for the request
HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
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