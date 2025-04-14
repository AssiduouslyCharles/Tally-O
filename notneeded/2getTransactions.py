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
    data = response.json()
    transactions = data.get("transactions", [])
    
    # Group transactions by order ID
    orders = {}
    for txn in transactions:
        order_id = txn.get("orderId", "N/A")
        orders.setdefault(order_id, []).append(txn)
    
    # Define CSV file and open for writing
    csv_file = "ebay_transactions_grouped1.csv"
    with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        
        # Write header row with a column for each transaction amount type
        writer.writerow([
            "Order ID", 
            "Sale Amount", 
            "Refund Amount", 
            "Shipping Label Cost",
            "Dispute Amount",
            "Credit Amount"
        ])
        
        # For each order, aggregate amounts by transaction type
        for order_id, txns in orders.items():
            sale_amounts = []
            refund_amounts = []
            shipping_label_costs = []
            dispute_amounts = []
            credit_amounts = []
            
            for txn in txns:
                txn_type = txn.get("transactionType", "").upper()  # Normalize to uppercase
                amount = txn.get("amount", {})
                amount_value = amount.get("value", "")
                
                if txn_type == "SALE":
                    sale_amounts.append(str(amount_value))
                elif txn_type == "REFUND":
                    refund_amounts.append(str(amount_value))
                elif txn_type == "SHIPPING_LABEL":
                    shipping_label_costs.append(str(amount_value))
                elif txn_type == "DISPUTE":
                    dispute_amounts.append(str(amount_value))
                elif txn_type == "CREDIT":
                    credit_amounts.append(str(amount_value))
            
            # Join amounts using semicolons in case there are multiple values
            sale_amt_str = "; ".join(sale_amounts)
            refund_amt_str = "; ".join(refund_amounts)
            shipping_label_amt_str = "; ".join(shipping_label_costs)
            dispute_amt_str = "; ".join(dispute_amounts)
            credit_amt_str = "; ".join(credit_amounts)
            
            writer.writerow([
                order_id,
                sale_amt_str,
                refund_amt_str,
                shipping_label_amt_str,
                dispute_amt_str,
                credit_amt_str
            ])
    
    print(f"CSV file '{csv_file}' created successfully.")
else:
    print("Error:", response.status_code, response.text)