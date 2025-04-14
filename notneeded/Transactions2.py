import requests
import json
import csv
import config

# eBay Finances API endpoint
EBAY_API_URL = "https://apiz.ebay.com/sell/finances/v1/transaction"

# Headers for the request
HEADERS = {
    "Authorization": f"Bearer {config.ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Query parameters
PARAMS = {
    "transaction_type": "ALL",  # Retrieve all types of transactions
    "limit": 1000,  # Fetch 50 transactions per request (max limit)
    "offset": 0  # Start from the first transaction
}

# File to store the transactions
CSV_FILE = "transactions2t.csv"

# Define CSV headers based on the API fields
CSV_HEADERS = [
    "Transaction ID", "Type", "Date", "Amount", "Fee Type", "Fee Amount",
    "Payout ID", "Order ID", "Item ID", "SKU", "Marketplace", "Status"
]

# Open CSV file for writing
with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(CSV_HEADERS)  # Write the headers

    while True:
        # Make API request
        response = requests.get(EBAY_API_URL, headers=HEADERS, params=PARAMS)

        if response.status_code == 200:
            data = response.json()
            transactions = data.get("transactions", [])

            # Process each transaction
            for transaction in transactions:
                transaction_id = transaction.get("transactionId", "N/A")
                transaction_type = transaction.get("transactionType", "N/A")
                transaction_date = transaction.get("transactionDate", "N/A")
                amount = transaction.get("amount", {}).get("value", "N/A")
                currency = transaction.get("amount", {}).get("currency", "N/A")
                fee_type = transaction.get("feeType", "N/A")
                fee_amount = transaction.get("feeAmount", {}).get("value", "N/A")
                payout_id = transaction.get("payoutId", "N/A")
                order_id = transaction.get("orderId", "N/A")
                item_id = transaction.get("lineItemId", "N/A")
                sku = transaction.get("sku", "N/A")
                marketplace = transaction.get("marketplace", "N/A")
                status = transaction.get("status", "N/A")

                # Write to CSV
                writer.writerow([
                    transaction_id, transaction_type, transaction_date,
                    f"{amount} {currency}", fee_type, fee_amount, payout_id,
                    order_id, item_id, sku, marketplace, status
                ])

            # Check if there are more pages
            total_transactions = data.get("total", 0)
            offset = PARAMS["offset"]
            limit = PARAMS["limit"]

            if offset + limit >= total_transactions:
                break  # No more transactions to fetch
            else:
                PARAMS["offset"] += limit  # Move to the next page

        else:
            print("❌ Error:", response.status_code, response.text)
            break  # Stop execution if API fails

print(f"✅ Transactions saved to {CSV_FILE}")