import sqlite3
import requests
import json
import config
import csv
from bs4 import BeautifulSoup
from datetime import datetime

############################
# DATABASE SETUP           #
############################

# Connect to (or create) a local SQLite database file
conn = sqlite3.connect('tally0.db')
cursor = conn.cursor()

# Create a table for transactions from the Finances API
cursor.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    order_id TEXT,
    line_item_id TEXT,
    transaction_type TEXT,
    transaction_date TEXT,
    amount_value REAL,
    sale_final_fee REAL,
    sale_fixed_fee REAL,
    sale_international_fee REAL,
    shipping_label_amount REAL,
    refund_amount REAL,
    refund_final_fee REAL,
    refund_fixed_fee REAL,
    dispute_amount REAL,
    credit_amount REAL,
    PRIMARY KEY (order_id, line_item_id, transaction_type, transaction_date)
)
''')

# Create a table for sold items from GetMyeBaySelling
cursor.execute('''
CREATE TABLE IF NOT EXISTS sold_items (
    order_id TEXT PRIMARY KEY,
    transaction_id TEXT,
    item_id TEXT,
    item_title TEXT,
    photo_url TEXT,
    list_date TEXT,
    sold_date TEXT,
    time_to_sell INTEGER,
    item_cost REAL,
    purchased_at TEXT,
    sku TEXT,
    quantity_sold INTEGER,
    sold_for_price REAL,
    shipping_paid REAL,
    final_fee REAL,
    fixed_final_fee REAL,
    international_fee REAL,
    cost_to_ship REAL,
    net_return REAL,
    roi REAL,
    net_profit_margin REAL,
    refund_to_buyer REAL,
    refund_owed REAL,
    refund_to_seller REAL
)
''')

conn.commit()

#################################
# STEP 1: GET TRANSACTIONS      #
#################################

def get_transactions_data():
    """
    Retrieve transactions from the Finances API, group them by order,
    and insert them into the 'transactions' table.
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

    # Insert each transaction record into the transactions table.
    # For this example, we'll extract a subset of fields from each transaction.
    for txn in all_transactions:
        order_id = txn.get("orderId", "N/A")
        # Assume marketplace fees and line item IDs reside in orderLineItems[0]
        line_item_id = txn.get("orderLineItems", [{}])[0].get("lineItemId", "")
        txn_type = txn.get("transactionType", "").upper()
        txn_date = txn.get("transactionDate", "")
        try:
            amount_value = float(txn.get("amount", {}).get("value", "0"))
        except Exception:
            amount_value = 0.0

        # Prepare fee values; if not available, default to 0.0
        sale_final_fee = sale_fixed_fee = sale_international_fee = 0.0
        shipping_label_amount = 0.0
        refund_amount = refund_final_fee = refund_fixed_fee = 0.0
        dispute_amount = 0.0
        credit_amount = 0.0

        fees = txn.get("orderLineItems", [{}])[0].get("marketplaceFees", [])
        for fee in fees:
            fee_type = fee.get("feeType", "")
            fee_amount = fee.get("amount", {}).get("value", "0")
            try:
                fee_amount = float(fee_amount)
            except Exception:
                fee_amount = 0.0
            if txn_type == "SALE":
                if fee_type == "FINAL_VALUE_FEE":
                    sale_final_fee = fee_amount
                elif fee_type == "FINAL_VALUE_FEE_FIXED_PER_ORDER":
                    sale_fixed_fee = fee_amount
                elif fee_type == "INTERNATIONAL_FEE":
                    sale_international_fee = fee_amount
            elif txn_type == "REFUND":
                if fee_type == "FINAL_VALUE_FEE":
                    refund_final_fee = fee_amount
                elif fee_type == "FINAL_VALUE_FEE_FIXED_PER_ORDER":
                    refund_fixed_fee = fee_amount
        if txn_type == "SHIPPING_LABEL":
            try:
                shipping_label_amount = float(amount_value)
            except Exception:
                shipping_label_amount = 0.0
        elif txn_type == "REFUND":
            try:
                refund_amount = float(amount_value)
            except Exception:
                refund_amount = 0.0
        elif txn_type == "DISPUTE":
            try:
                dispute_amount = float(amount_value)
            except Exception:
                dispute_amount = 0.0
        elif txn_type == "CREDIT":
            try:
                credit_amount = float(amount_value)
            except Exception:
                credit_amount = 0.0

        # Insert the transaction record into the transactions table.
        cursor.execute('''
        INSERT OR REPLACE INTO transactions (
            order_id, line_item_id, transaction_type, transaction_date, amount_value,
            sale_final_fee, sale_fixed_fee, sale_international_fee,
            shipping_label_amount, refund_amount, refund_final_fee, refund_fixed_fee,
            dispute_amount, credit_amount
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_id, line_item_id, txn_type, txn_date, amount_value,
            sale_final_fee, sale_fixed_fee, sale_international_fee,
            shipping_label_amount, refund_amount, refund_final_fee, refund_fixed_fee,
            dispute_amount, credit_amount
        ))
    conn.commit()
    print("Transactions data inserted into the database.")

#################################
# STEP 2: GET MYEBAY SOLD DATA  #
#################################

def get_sold_list_data():
    """
    Retrieves sold items data from GetMyeBaySelling and inserts it into the sold_items table.
    """
    EBAY_API_URL = "https://api.ebay.com/ws/api.dll"
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
    if response.status_code != 200:
        print("Error retrieving sold list:", response.status_code, response.text)
        return
    soup = BeautifulSoup(response.text, "xml")
    transactions = soup.find_all("Transaction")
    
    for transaction in transactions:
        item = transaction.find("Item")
        order_id = transaction.find("OrderLineItemID").text if transaction.find("OrderLineItemID") else "N/A"
        transaction_id = transaction.find("TransactionID").text if transaction.find("TransactionID") else "N/A"
        item_id = item.find("ItemID").text if item.find("ItemID") else "N/A"
        item_title = item.find("Title").text if item.find("Title") else "N/A"
        photo_url = item.find("ViewItemURL").text if item.find("ViewItemURL") else "N/A"
        list_date = item.find("StartTime").text if item.find("StartTime") else "N/A"
        sold_date = item.find("EndTime").text if item.find("EndTime") else "N/A"
        if list_date != "N/A" and sold_date != "N/A":
            list_dt = datetime.strptime(list_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            sold_dt = datetime.strptime(sold_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            time_to_sell = (sold_dt - list_dt).days
        else:
            time_to_sell = None
        # The following fields may be updated later from transactional fees data.
        item_cost = None
        purchased_at = None
        sku = item.find("SKU").text if item.find("SKU") else None
        quant_sold = item.find("QuantitySold").text if item.find("QuantitySold") else None
        sold_for_price = transaction.find("TransactionPrice").text if transaction.find("TransactionPrice") else None
        shipping_paid = item.find("ShippingServiceCost").text if item.find("ShippingServiceCost") else None
        
        fixed_final_fee = None
        final_fee = None
        international_fee = None
        cost_to_ship = None
        net_return = None
        roi = None
        net_profit_margin = None
        refund_to_buyer = None
        refund_owed = None
        refund_to_seller = None
        
        # Insert or update sold_items record (using order_id as primary key)
        cursor.execute('''
        INSERT OR REPLACE INTO sold_items (
            order_id, transaction_id, item_id, item_title, photo_url, list_date, sold_date,
            time_to_sell, item_cost, purchased_at, sku, quantity_sold, sold_for_price,
            shipping_paid, final_fee, fixed_final_fee, international_fee, cost_to_ship,
            net_return, roi, net_profit_margin, refund_to_buyer, refund_owed, refund_to_seller
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_id, transaction_id, item_id, item_title, photo_url, list_date, sold_date,
            time_to_sell, item_cost, purchased_at, sku, quant_sold, sold_for_price,
            shipping_paid, final_fee, fixed_final_fee, international_fee, cost_to_ship,
            net_return, roi, net_profit_margin, refund_to_buyer, refund_owed, refund_to_seller
        ))
    conn.commit()
    print("Sold items data inserted into the database.")

#################################
# STEP 3: UPDATE SOLD DATA      #
#################################

def update_sold_data():
    """
    Matches sold items with transactions data (using Transaction ID from sold list
    and matching with Line Item ID in transactions table) and updates the sold_items table.
    Mapping:
      - Final Fee = Final Fee from transactions (for SALE)
      - Fixed Final Fee = Fixed Final Fee from transactions (for SALE)
      - International Fee = International Fee from transactions (for SALE)
      - Cost To Ship = Cost To Ship from transactions (for SHIPPING_LABEL)
      - Refund Owed = Refund Owed from transactions (for REFUND)
      - Refund To Seller = Refund Final Fee + Refund Fixed Fee (for REFUND)
    """
    # For this example, let's update only the fields relevant to SALE and REFUND.
    # Note: You may need to adjust the JOIN conditions based on your data.
    update_query = '''
    UPDATE sold_items SET
        final_fee = (
            SELECT sale_final_fee
            FROM transactions
            WHERE transactions.line_item_id = sold_items.transaction_id
              AND transactions.transaction_type = 'SALE'
        ),
        fixed_final_fee = (
            SELECT sale_fixed_fee
            FROM transactions
            WHERE transactions.line_item_id = sold_items.transaction_id
              AND transactions.transaction_type = 'SALE'
        ),
        international_fee = (
            SELECT sale_international_fee
            FROM transactions
            WHERE transactions.line_item_id = sold_items.transaction_id
              AND transactions.transaction_type = 'SALE'
        ),
        cost_to_ship = (
            SELECT shipping_label_amount
            FROM transactions
            WHERE transactions.line_item_id = sold_items.transaction_id
              AND transactions.transaction_type = 'SHIPPING_LABEL'
        ),
        refund_owed = (
            SELECT refund_amount
            FROM transactions
            WHERE transactions.line_item_id = sold_items.transaction_id
              AND transactions.transaction_type = 'REFUND'
        ),
        refund_to_seller = (
            SELECT (refund_final_fee + refund_fixed_fee)
            FROM transactions
            WHERE transactions.line_item_id = sold_items.transaction_id
              AND transactions.transaction_type = 'REFUND'
        )
    WHERE EXISTS (
        SELECT 1 FROM transactions
        WHERE transactions.line_item_id = sold_items.transaction_id
    )
    '''
    cursor.execute(update_query)
    conn.commit()
    print("Sold data updated with financial data from transactions.")

#######################
# MAIN APPLICATION    #
#######################

def main():
    # Step 1: Get transactions data and update the transactions table
    get_transactions_data()
    
    # Step 2: Get sold list data and update the sold_items table
    get_sold_list_data()
    
    # Step 3: Update sold items data from transactions
    update_sold_data()

if __name__ == "__main__":
    main()
    conn.close()