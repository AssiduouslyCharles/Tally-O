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

# Pagination parameters
limit = 1000
offset = 0
PARAMS = {
    "transaction_type": "ALL",
    "limit": limit,
    "offset": offset
}

# Retrieve all transactions across pages
all_transactions = []
while True:
    PARAMS["offset"] = offset
    response = requests.get(EBAY_API_URL, headers=HEADERS, params=PARAMS)
    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        break

    data = response.json()
    transactions = data.get("transactions", [])
    if not transactions:
        break

    all_transactions.extend(transactions)
    offset += limit

# Group transactions by order ID.
orders = {}
for txn in all_transactions:
    order_id = txn.get("orderId", "N/A")
    if order_id not in orders:
        orders[order_id] = {
            "line_item_ids": set(),  # use a set to avoid duplicates
            "sale_amounts": [],
            "sale_transaction_dates": [],
            "sale_final_value_fee": [],
            "sale_fixed_final_value_fee": [],
            "sale_international_fee": [],
            "shipping_label_amounts": [],
            "refund_amounts": [],
            "refund_final_value_fee": [],
            "refund_fixed_final_value_fee": [],
            "dispute_amounts": [],
            "credit_amounts": []
        }
    
    # Get the line item id from orderLineItems (assuming it exists)
    line_item_id = txn.get("orderLineItems", [{}])[0].get("lineItemId", "")
    if line_item_id:
        orders[order_id]["line_item_ids"].add(line_item_id)
    
    txn_type = txn.get("transactionType", "").upper()
    txn_date = txn.get("transactionDate", "")
    amount_value = txn.get("amount", {}).get("value", "")
    fees = txn.get("orderLineItems", [{}])[0].get("marketplaceFees", [])
    
    if txn_type == "SALE":
        orders[order_id]["sale_amounts"].append(amount_value)
        orders[order_id]["sale_transaction_dates"].append(txn_date)
        for fee in fees:
            fee_type = fee.get("feeType", "")
            fee_amount = fee.get("amount", {}).get("value", "")
            if fee_type == "FINAL_VALUE_FEE":
                orders[order_id]["sale_final_value_fee"].append(fee_amount)
            elif fee_type == "FINAL_VALUE_FEE_FIXED_PER_ORDER":
                orders[order_id]["sale_fixed_final_value_fee"].append(fee_amount)
            elif fee_type == "INTERNATIONAL_FEE":
                orders[order_id]["sale_international_fee"].append(fee_amount)
    elif txn_type == "SHIPPING_LABEL":
        orders[order_id]["shipping_label_amounts"].append(amount_value)
    elif txn_type == "REFUND":
        orders[order_id]["refund_amounts"].append(amount_value)
        for fee in fees:
            fee_type = fee.get("feeType", "")
            fee_amount = fee.get("amount", {}).get("value", "")
            if fee_type == "FINAL_VALUE_FEE":
                orders[order_id]["refund_final_value_fee"].append(fee_amount)
            elif fee_type == "FINAL_VALUE_FEE_FIXED_PER_ORDER":
                orders[order_id]["refund_fixed_final_value_fee"].append(fee_amount)
    elif txn_type == "DISPUTE":
        orders[order_id]["dispute_amounts"].append(amount_value)
    elif txn_type == "CREDIT":
        orders[order_id]["credit_amounts"].append(amount_value)

# Overwrite the CSV file each time by using "w" mode.
csv_file = "ebay_transactions_grouped.csv"
with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    
    # Write header row
    writer.writerow([
        "Order ID",
        "Line Item IDs",
        "Sale Amount Value",
        "Sale Transaction Date",
        "Final Fee",
        "Fixed Final Fee",
        "International Fee",
        "Cost To Ship",
        "Refund Owed",
        "Refund Final Fee",
        "Refund Fixed Final Fee",
        "Dispute Amount Value",
        "Credit Amount Value"
    ])
    
    # Write data rows for each order.
    for order_id, values in orders.items():
        line_item_ids = "; ".join(sorted(values["line_item_ids"]))
        sale_amounts = "; ".join(values["sale_amounts"])
        sale_txn_dates = "; ".join(values["sale_transaction_dates"])
        sale_final_fee = "; ".join(values["sale_final_value_fee"])
        sale_fixed_fee = "; ".join(values["sale_fixed_final_value_fee"])
        sale_international_fee = "; ".join(values["sale_international_fee"])
        
        # Sum shipping label amounts and format to 2 decimals.
        try:
            shipping_label_sum = sum(float(val) for val in values["shipping_label_amounts"] if val)
            shipping_label_amount = f"{shipping_label_sum:.2f}"
        except Exception:
            shipping_label_amount = "; ".join(values["shipping_label_amounts"])
        
        refund_amounts = "; ".join(values["refund_amounts"])
        refund_final_fee = "; ".join(values["refund_final_value_fee"])
        refund_fixed_fee = "; ".join(values["refund_fixed_final_value_fee"])
        dispute_amounts = "; ".join(values["dispute_amounts"])
        credit_amounts = "; ".join(values["credit_amounts"])
        
        writer.writerow([
            order_id,
            line_item_ids,
            sale_amounts,
            sale_txn_dates,
            sale_final_fee,
            sale_fixed_fee,
            sale_international_fee,
            shipping_label_amount,
            refund_amounts,
            refund_final_fee,
            refund_fixed_fee,
            dispute_amounts,
            credit_amounts
        ])

print(f"CSV file '{csv_file}' overwritten successfully.")