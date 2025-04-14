import requests
import json
import config
import csv

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
    "limit": 1000,
    "offset": 0
}

# Make the API request
response = requests.get(EBAY_API_URL, headers=HEADERS, params=PARAMS)

if response.status_code == 200:
    print(response.text)
else:
    print("Error:", response.status_code, response.text)