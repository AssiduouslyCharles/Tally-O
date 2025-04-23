import os
from dotenv import load_dotenv
import base64
import requests
from urllib.parse import urlencode
from flask import Flask, jsonify, render_template, redirect, request, session, url_for
from datetime import timedelta, datetime
import sqlite3
from bs4 import BeautifulSoup

# Determine the directory where this file is located
basedir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.abspath(os.path.join(basedir, '..'))  # .../Tally-O
db_path = os.path.join(project_root, 'tally0.db')

# Construct the full path to the .env file
dotenv_path = os.path.join(basedir, '.env')
# Load environment variables from the specified .env file
load_dotenv(dotenv_path)

app = Flask(__name__)

# Use a strong random value for the secret key or load it from your environment
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

# Secure session configuration for Session-Based Storage:
app.config.update(
    SESSION_COOKIE_SECURE=True,       # Send cookies only over HTTPS
    SESSION_COOKIE_HTTPONLY=True,       # Disallow JavaScript to access the cookie
    SESSION_COOKIE_SAMESITE='Lax',        # Helps mitigate CSRF attacks
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30)  # Session lifetime
)

# eBay API credentials from the environment
EBAY_CLIENT_ID = os.environ.get("EBAY_CLIENT_ID")            # Your eBay Client ID (Application ID)
EBAY_CLIENT_SECRET = os.environ.get("EBAY_CLIENT_SECRET")    # Your eBay Client Secret (Cert ID)
EBAY_REDIRECT_URI = os.environ.get("EBAY_REDIRECT_URI")

# OAuth endpoints
EBAY_OAUTH_URL = "https://auth.ebay.com/oauth2/authorize"
EBAY_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

# Define the scope of access you need (space-separated list)
EBAY_SCOPES = ("https://api.ebay.com/oauth/api_scope "
               "https://api.ebay.com/oauth/api_scope/sell.marketing.readonly "
               "https://api.ebay.com/oauth/api_scope/sell.marketing "
               "https://api.ebay.com/oauth/api_scope/sell.inventory.readonly "
               "https://api.ebay.com/oauth/api_scope/sell.inventory "
               "https://api.ebay.com/oauth/api_scope/sell.account.readonly "
               "https://api.ebay.com/oauth/api_scope/sell.account "
               "https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly "
               "https://api.ebay.com/oauth/api_scope/sell.fulfillment "
               "https://api.ebay.com/oauth/api_scope/sell.analytics.readonly "
               "https://api.ebay.com/oauth/api_scope/sell.finances "
               "https://api.ebay.com/oauth/api_scope/sell.payment.dispute "
               "https://api.ebay.com/oauth/api_scope/commerce.identity.readonly "
               "https://api.ebay.com/oauth/api_scope/sell.reputation "
               "https://api.ebay.com/oauth/api_scope/sell.reputation.readonly "
               "https://api.ebay.com/oauth/api_scope/commerce.notification.subscription "
               "https://api.ebay.com/oauth/api_scope/commerce.notification.subscription.readonly "
               "https://api.ebay.com/oauth/api_scope/sell.stores "
               "https://api.ebay.com/oauth/api_scope/sell.stores.readonly "
               "https://api.ebay.com/oauth/scope/sell.edelivery")

@app.route('/')
def index():
    # Serve the home page – ensure you have an index.html in your templates folder.
    return render_template('index.html')

@app.route('/ping')
def ping():
    return "pong"

@app.route('/init-db')
def init_db():
    schema_file = os.path.join(project_root, 'db', 'schema.sql')
    with sqlite3.connect(db_path) as conn:
        with open(schema_file, 'r') as f:
            conn.executescript(f.read())
    return f"Initialized DB at {db_path}", 200

@app.route('/api/test')
def test_api():
    return jsonify({"message": "Hello, world!"})

@app.route('/auth/ebay/login')
def ebay_login():
    # Create the parameter dictionary for the OAuth URL
    params = {
        "client_id": EBAY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": EBAY_REDIRECT_URI,
        "scope": EBAY_SCOPES,
    }
    # Encode query parameters safely
    query_string = urlencode(params)
    auth_url = f"{EBAY_OAUTH_URL}?{query_string}"
    
    # Redirect the user to the constructed OAuth URL
    return redirect(auth_url)

@app.route('/auth/ebay/callback')
def ebay_callback():
    # Retrieve the authorization code provided by eBay
    code = request.args.get('code')
    if not code:
        return "Error: Missing authorization code.", 400

    # Construct the Basic Authentication header required by eBay
    auth_header = base64.b64encode(f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}".encode()).decode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth_header}"
    }
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": EBAY_REDIRECT_URI
    }

    # Exchange the authorization code for an access token
    token_response = requests.post(EBAY_TOKEN_URL, headers=headers, data=payload)
    if token_response.status_code != 200:
        return f"Error fetching token: {token_response.text}", 400

    token_data = token_response.json()

    # Store tokens in the session. With our secure session configuration,
    # these tokens will be stored as signed cookies (client-side) for the duration of the session.
    session['access_token'] = token_data.get('access_token')
    session['refresh_token'] = token_data.get('refresh_token')

    # Redirect to the dashboard or home page upon successful login
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    # Retrieve the access token from the session
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('ebay_login'))
    
    # Render the dashboard page with the token. Adjust your dashboard.html accordingly.
    return render_template('dashboard.html', token=access_token)
'''
@app.route('/inventory')
def inventory():
    # In a real app, you’d fetch inventory data here
    return render_template('inventory.html')

@app.route('/sold')
def inventory():
    # In a real app, you’d fetch inventory data here
    return render_template('sold.html')

@app.route('/insights')
def inventory():
    # In a real app, you’d fetch inventory data here
    return render_template('insights.html')
'''
###################################
# Helper Functions for Proxying   #
###################################

def get_transactions_data(cursor, access_token):
    """
    Retrieve transactions from the eBay Finances API and insert the records 
    into the 'transactions' table. (Table schema is managed separately via schema.sq)
    """
    EBAY_API_URL = "https://api.ebay.com/sell/finances/v1/transaction"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    limit = 1000
    offset = 0
    params = {
        "transaction_type": "ALL",
        "limit": limit,
        "offset": offset
    }
    all_transactions = []
    while True:
        params["offset"] = offset
        response = requests.get(EBAY_API_URL, headers=headers, params=params)
        if response.status_code != 200:
            print("Error retrieving transactions:", response.status_code, response.text)
            break
        data = response.json()
        transactions = data.get("transactions", [])
        if not transactions:
            break
        all_transactions.extend(transactions)
        offset += limit

    for txn in all_transactions:
        order_id = txn.get("orderId", "N/A")
        line_item_id = txn.get("orderLineItems", [{}])[0].get("lineItemId", "")
        txn_type = txn.get("transactionType", "").upper()
        txn_date = txn.get("transactionDate", "")
        try:
            amount_value = float(txn.get("amount", {}).get("value", "0"))
        except Exception:
            amount_value = 0.0

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
    print("Transactions data inserted into the database.")

def get_sold_list_data(cursor, access_token):
    """
    Retrieve sold items data from GetMyeBaySelling and insert the records into 
    the 'sold_items' table (schema managed via schema.sq).
    """
    EBAY_API_URL = "https://api.ebay.com/ws/api.dll"
    # Retrieve eBay developer credentials from environment variables
    EBAY_DEV_ID = os.environ.get("EBAY_DEV_ID")
    EBAY_APP_ID = os.environ.get("EBAY_APP_ID")
    EBAY_CERT_ID = os.environ.get("EBAY_CERT_ID")
    
    headers = {
        "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
        "X-EBAY-API-DEV-NAME": EBAY_DEV_ID,
        "X-EBAY-API-APP-NAME": EBAY_APP_ID,
        "X-EBAY-API-CERT-NAME": EBAY_CERT_ID,
        "X-EBAY-API-CALL-NAME": "GetMyeBaySelling",
        "X-EBAY-API-SITEID": "0",
        "Content-Type": "text/xml"
    }
    
    XML_PAYLOAD = f"""<?xml version="1.0" encoding="utf-8"?>
    <GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
        <RequesterCredentials>
            <eBayAuthToken>{access_token}</eBayAuthToken>
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
    
    response = requests.post(EBAY_API_URL, headers=headers, data=XML_PAYLOAD)
    if response.status_code != 200:
        print("Error retrieving sold list:", response.status_code, response.text)
        return
    soup = BeautifulSoup(response.text, "xml")
    transactions = soup.find_all("Transaction")
    
    for transaction in transactions:
        item = transaction.find("Item")
        order_id = transaction.find("OrderLineItemID").text if transaction.find("OrderLineItemID") else "N/A"
        transaction_id = transaction.find("TransactionID").text if transaction.find("TransactionID") else "N/A"
        item_id = item.find("ItemID").text if item and item.find("ItemID") else "N/A"
        item_title = item.find("Title").text if item and item.find("Title") else "N/A"
        photo_url = item.find("ViewItemURL").text if item and item.find("ViewItemURL") else "N/A"
        list_date = item.find("StartTime").text if item and item.find("StartTime") else "N/A"
        sold_date = item.find("EndTime").text if item and item.find("EndTime") else "N/A"
        if list_date != "N/A" and sold_date != "N/A":
            list_dt = datetime.strptime(list_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            sold_dt = datetime.strptime(sold_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            time_to_sell = (sold_dt - list_dt).days
        else:
            time_to_sell = None
        item_cost = None
        purchased_at = None
        sku = item.find("SKU").text if item and item.find("SKU") else None
        quant_sold = item.find("QuantitySold").text if item and item.find("QuantitySold") else None
        sold_for_price = transaction.find("TransactionPrice").text if transaction.find("TransactionPrice") else None
        shipping_paid = item.find("ShippingServiceCost").text if item and item.find("ShippingServiceCost") else None
        
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
    print("Sold items data inserted into the database.")

def update_sold_data(cursor):
    """
    Update sold items data with financial details from transactions.
    """
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
    print("Sold items updated with financial data from transactions.")

###################################
# New Route to Update eBay Data   #
###################################

@app.route('/update-ebay-data')
def update_ebay_data():
    # Check if the user is authenticated (i.e. has an access token in session)
    access_token = session.get("access_token")
    if not access_token:
        return redirect(url_for("ebay_login"))
    
    try:
        # Open a connection to the SQLite database (change the path if needed)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Call helper functions to update the database
        get_transactions_data(cursor, access_token)
        get_sold_list_data(cursor, access_token)
        update_sold_data(cursor)
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
    
    return jsonify({"status": "eBay data updated successfully"})

@app.route('/api/transactions')
def api_transactions():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions")
        rows = cursor.fetchall()
        # Optionally, convert rows to a list of dictionaries for JSON serialization.
        columns = [column[0] for column in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
    return jsonify(data)

@app.route('/api/sold-items')
def api_sold_items():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sold_items")
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
    return jsonify(data)


if __name__ == '__main__':
    # Run your Flask application in debug mode during development
    app.run(debug=True)
