import requests
import json
import config
import csv
from bs4 import BeautifulSoup
from datetime import datetime
import os

############################
# STEP 1: GET TRANSACTIONS #
############################

def get_transactions():
    """
    Retrieves all transactions from the eBay Finances API and groups them by order.
    Overwrites the CSV file "ebay_transactions_grouped.csv".
    """
    EBAY_API_URL = "https://apiz.ebay.com/sell/finances/v1/transaction"
    HEADERS = {
        "Authorization": f"Bearer {config.ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    limit = 1000
    offset = 0
    PARAMS = {
        "transaction_type": "ALL",
        "limit": limit,
        "offset": offset
    }
    all_transactions = []
    while True:
        PARAMS["offset"] = offset
        response = requests.get(EBAY_API_URL, headers=HEADERS, params=PARAMS)
        if response.status_code != 200:
            print("Error retrieving transactions:", response.status_code, response.text)
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
    
    csv_file = "TRANSACTIONS.csv"
    with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
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
        for order_id, values in orders.items():
            line_item_ids = "; ".join(sorted(values["line_item_ids"]))
            sale_amounts = "; ".join(values["sale_amounts"])
            sale_txn_dates = "; ".join(values["sale_transaction_dates"])
            sale_final_fee = "; ".join(values["sale_final_value_fee"])
            sale_fixed_fee = "; ".join(values["sale_fixed_final_value_fee"])
            sale_international_fee = "; ".join(values["sale_international_fee"])
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
    print(f"CSV file '{csv_file}' written successfully.")
    return csv_file

############################################
# STEP 2: GET MYEBAYSOLD SOLD ITEMS DATA   #
############################################

def get_sold_list():
    """
    Retrieves sold items data using the GetMyeBaySelling API call and writes it to sold_list.csv.
    """
    EBAY_API_URL = "https://api.ebay.com/ws/api.dll"  # For production; for sandbox, use appropriate URL
    HEADERS = {
        "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
        "X-EBAY-API-DEV-NAME": config.EBAY_DEV_ID,
        "X-EBAY-API-APP-NAME": config.EBAY_APP_ID,
        "X-EBAY-API-CERT-NAME": config.EBAY_CERT_ID,
        "X-EBAY-API-CALL-NAME": "GetMyeBaySelling",
        "X-EBAY-API-SITEID": "0",
        "Content-Type": "text/xml"
    }
    
    XML_PAYLOAD = f"""<?xml version="1.0" encoding="utf-8"?>
    <GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
        <RequesterCredentials>
            <eBayAuthToken>{config.ACCESS_TOKEN}</eBayAuthToken>
        </RequesterCredentials>
        <SoldList>
            <Include>true</Include>
            <DurationInDays>60</DurationInDays>
            <Pagination>
                <EntriesPerPage>200</EntriesPerPage>
                <PageNumber>1</PageNumber>
            </Pagination>
        </SoldList>
    </GetMyeBaySellingRequest>"""
    
    response = requests.post(EBAY_API_URL, headers=HEADERS, data=XML_PAYLOAD)
    csv_file = "SOLD_LISTINGS.csv"
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "xml")
        transactions = soup.find_all("Transaction")
        sold_items = []
        for transaction in transactions:
            item = transaction.find("Item")
            order_id = transaction.find("OrderLineItemID").text if transaction.find("OrderLineItemID") else "N/A"
            transaction_id = transaction.find("TransactionID").text if transaction.find("TransactionID") else "N/A"
            item_id = item.find("ItemID").text if item.find("ItemID") else "N/A"
            item_title = item.find("Title").text if item.find("Title") else "N/A"
            photo_URL = item.find("ViewItemURL").text if item.find("ViewItemURL") else "N/A"
            list_date = item.find("StartTime").text if item.find("StartTime") else "N/A"
            sold_date = item.find("EndTime").text if item.find("EndTime") else "N/A"
            if list_date != "N/A" and sold_date != "N/A":
                list_dt = datetime.strptime(list_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                sold_dt = datetime.strptime(sold_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                time_to_sell = (sold_dt - list_dt).days
            else:
                time_to_sell = "N/A"
            item_cost = ""
            purchased_at = ""
            sku = item.find("SKU").text if item.find("SKU") else ""
            quant_sold = item.find("QuantitySold").text if item.find("QuantitySold") else "N/A"
            sold_for_price = transaction.find("TransactionPrice").text if transaction.find("TransactionPrice") else "N/A"
            shipping_paid = item.find("ShippingServiceCost").text if item.find("ShippingServiceCost") else "N/A"
            
            # Initialize empty fields for financial data to be updated later.
            fixed_final_fee = ""
            final_fee = ""
            international_fee = ""
            cost_to_ship = ""
            net_return = ""
            roi = ""
            net_profit_margin = ""
            refund_to_buyer = ""
            refund_owed = ""
            refund_to_seller = ""
            
            sold_items.append([order_id, transaction_id, item_id, item_title, photo_URL, list_date, sold_date, time_to_sell, item_cost, purchased_at, sku, quant_sold, sold_for_price, shipping_paid, fixed_final_fee, final_fee, international_fee, cost_to_ship, net_return, roi, net_profit_margin, refund_to_buyer, refund_owed, refund_to_seller])
        
        with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Order ID", "Transaction ID", "Item ID", "Title", "Photo URL", "List Date", "Sold Date", "Time To Sell(days)", "Item Cost", "Purchased At", "SKU", "Quantity Sold", "Sold For Price", "Shipping Paid", "Fixed Final Fee", "Final Fee", "International Fee", "Cost To Ship", "Net Return", "ROI", "Net Profit Margin", "Refund To Buyer", "Refund Owed", "Refund To Seller"])
            writer.writerows(sold_items)
        
        print(f"Sold list CSV '{csv_file}' saved successfully.")
        return csv_file
    else:
        print("Error:", response.status_code, response.text)
        return None

###################################################
# STEP 3: UPDATE SOLD DATABASE WITH SOLDLIST CSV  #
###################################################

def update_sold_list(sold_list_file, transactions_file):
    """
    Matches the sold list CSV with the transactions CSV,
    using Transaction ID from sold list to match with Line Item ID from transactions CSV,
    and updates missing corresponding financial values.
    Writes out a new CSV file named 'sold_list_updated.csv'.
    Mapping:
      - Final Fee = Final Fee
      - Fixed Final Fee = Fixed Final Fee
      - International Fee = International Fee
      - Cost To Ship = Cost To Ship
      - Refund Owed = Refund Owed
      - Refund To Seller = Refund Final Fee + Refund Fixed Final Fee
    """
    output_file = "SOLD_LISTINGS_UPDATED.csv"

    # Read the transactions CSV into a dictionary keyed on "Line Item IDs"
    transactions_dict = {}
    with open(transactions_file, mode="r", newline="", encoding="utf-8") as tf:
        reader = csv.DictReader(tf)
        for row in reader:
            # Extract all line item IDs (they may be semicolon separated)
            line_item_ids_str = row.get("Line Item IDs", "")
            if line_item_ids_str:
                for part in [p.strip() for p in line_item_ids_str.split(";")]:
                    if part:
                        transactions_dict[part] = row

    # Read the sold list CSV
    sold_list_rows = []
    with open(sold_list_file, mode="r", newline="", encoding="utf-8") as sf:
        reader = csv.DictReader(sf)
        sold_list_fieldnames = reader.fieldnames[:]  # copy header
        for row in reader:
            sold_list_rows.append(row)

    # Define new columns if not present.
    new_columns = [
        "Final Fee",
        "Fixed Final Fee",
        "International Fee",
        "Cost To Ship",
        "Refund Owed",
        "Refund To Seller"
    ]
    for col in new_columns:
        if col not in sold_list_fieldnames:
            sold_list_fieldnames.append(col)

    # Process each sold list row by matching Transaction ID with a key in transactions_dict
    for row in sold_list_rows:
        transaction_id = row.get("Transaction ID", "").strip()
        matched = None
        if transaction_id and transaction_id in transactions_dict:
            matched = transactions_dict[transaction_id]
        if matched:
            row["Final Fee"] = matched.get("Final Fee", "")
            row["Fixed Final Fee"] = matched.get("Fixed Final Fee", "")
            row["International Fee"] = matched.get("International Fee", "")
            row["Cost To Ship"] = matched.get("Cost To Ship", "")
            row["Refund Owed"] = matched.get("Refund Owed", "")
            try:
                refund_final = float(matched.get("Refund Final Fee", "0") or "0")
                refund_fixed = float(matched.get("Refund Fixed Fee", "0") or "0")
                row["Refund To Seller"] = f"{(refund_final + refund_fixed):.2f}"
            except Exception:
                row["Refund To Seller"] = ""
        else:
            for col in new_columns:
                row[col] = ""

    # Write out the updated sold list CSV
    with open(output_file, mode="w", newline="", encoding="utf-8") as outf:
        writer = csv.DictWriter(outf, fieldnames=sold_list_fieldnames)
        writer.writeheader()
        for row in sold_list_rows:
            writer.writerow(row)
    
    print(f"Updated sold list CSV written to '{output_file}'.")
    return output_file

####################
# MAIN APPLICATION #
####################

def main():
    # Step 1: Get transactions, producing transactions CSV.
    transactions_csv = get_transactions()
    if not transactions_csv:
        print("Failed to retrieve transactions.")
        return
    
    # Step 2: Get sold list from GetMyeBaySelling, producing sold list CSV.
    sold_list_csv = get_sold_list()
    if not sold_list_csv:
        print("Failed to retrieve sold list.")
        return

    # Step 3: Update sold list CSV using transactions CSV.
    update_sold_list(sold_list_csv, transactions_csv)

if __name__ == "__main__":
    main()