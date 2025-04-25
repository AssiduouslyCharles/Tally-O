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

@app.route('/inventory')
def inventory():
    # In a real app, you’d fetch inventory data here
    return render_template('inventory.html')

@app.route('/sold')
def sold():
    # In a real app, you’d fetch inventory data here
    return render_template('sold.html')

@app.route('/insights')
def insights():
    # In a real app, you’d fetch inventory data here
    return render_template('insights.html')

###################################
# Helper Functions for Proxying   #
###################################

def get_inventory_data(cursor, access_token):
    """
    Retrieve active inventory items from eBay (GetMyeBaySelling → ActiveList),
    and upsert them into an SQLite table 'inventory_items'.
    """
    EBAY_API_URL = "https://api.ebay.com/ws/api.dll"
    EBAY_DEV_ID  = os.environ.get("EBAY_DEV_ID")
    EBAY_APP_ID  = os.environ.get("EBAY_APP_ID")
    EBAY_CERT_ID = os.environ.get("EBAY_CERT_ID")

    headers = {
        "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
        "X-EBAY-API-DEV-NAME":            EBAY_DEV_ID,
        "X-EBAY-API-APP-NAME":            EBAY_APP_ID,
        "X-EBAY-API-CERT-NAME":           EBAY_CERT_ID,
        "X-EBAY-API-CALL-NAME":           "GetMyeBaySelling",
        "X-EBAY-API-SITEID":              "0",
        "Content-Type":                   "text/xml",
    }

    page = 1
    total = 0

    while True:
        # 1) Build the XML asking for the gallery URL as well
        xml = f"""<?xml version="1.0" encoding="utf-8"?>
        <GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
        <RequesterCredentials>
        <eBayAuthToken>{access_token}</eBayAuthToken>
        </RequesterCredentials>
        <ActiveList>
            <Include>true</Include>
            <Pagination>
                <EntriesPerPage>200</EntriesPerPage>
                <PageNumber>{page}</PageNumber>
            </Pagination>
        </ActiveList>
        </GetMyeBaySellingRequest>"""

        resp = requests.post(EBAY_API_URL, headers=headers, data=xml)
        if resp.status_code != 200:
            print("Error fetching inventory (page", page, "):", resp.status_code, resp.text)
            break

        soup = BeautifulSoup(resp.text, "xml")
        active = soup.find("ActiveList")
        if not active:
            break

        items = active.find_all("Item")
        if not items:
            break

        for item in items:
            # Extract fields (with safe defaults)
            item_id     = item.find("ItemID").text if item.find("ItemID") else None
            title       = item.find("Title").text  if item.find("Title") else ""
            photo_url = item.find("PictureDetails").text if item.find("PictureDetails") else ""
            price       = item.find("CurrentPrice") or item.find("BuyItNowPrice")
            list_price  = float(price.text) if (price and price.text) else 0.0
            start_time  = item.find("StartTime").text if item.find("StartTime") else ""
            # blank placeholders for manual columns
            item_cost          = None
            purchased_at       = None
            storage_loc        = None
            sku                = item.find("SKU").text if item.find("SKU") else ""
            qty_avail          = int(item.find("QuantityAvailable").text) if item.find("QuantityAvailable") else 0

            # Upsert into SQLite
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_items (
              item_id           TEXT    PRIMARY KEY,
              item_title        TEXT,
              photo_url         TEXT,
              list_price        REAL,
              list_date         TEXT,
              item_cost         REAL,
              available_quantity INTEGER,
              purchased_at      TEXT,
              sku               TEXT,
              storage_location TEXT
            );
            """)
            cursor.execute("""
            INSERT INTO inventory_items (
              item_id, item_title, photo_url, list_price,
              list_date, item_cost, available_quantity,
              purchased_at, sku, storage_location
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
              item_title        = excluded.item_title,
              photo_url         = excluded.photo_url,
              list_price        = excluded.list_price,
              list_date         = excluded.list_date,
              sku               = excluded.sku,
              available_quantity= excluded.available_quantity;
            """, (
              item_id, title, photo_url, list_price,
              start_time, item_cost, qty_avail,
              purchased_at, sku, storage_loc
            ))
            total += 1

        page += 1

    print(f"Upserted {total} inventory items into 'inventory_items'.")


def get_transactions_data(cursor, access_token):
    """
    Retrieve transactions from the eBay Finances API,
    group them by order (one value per txn type),
    and insert into SQLite table 'transactions_grouped'.
    """
    EBAY_API_URL = "https://apiz.ebay.com/sell/finances/v1/transaction"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
    }

    # 1) Fetch all transactions
    limit, offset = 1000, 0
    all_txns = []
    while True:
        params = {"transaction_type": "ALL", "limit": limit, "offset": offset}
        resp = requests.get(EBAY_API_URL, headers=headers, params=params)
        if resp.status_code == 204:
            break
        if resp.status_code != 200:
            raise RuntimeError(f"eBay getTransactions failed ({resp.status_code}): {resp.text}")
        page = resp.json().get("transactions", [])
        if not page:
            break
        all_txns.extend(page)
        offset += limit

    print(f"Fetched {len(all_txns)} transactions")

    # 2) Group by orderId, but only keep the first value seen per type
    orders = {}
    for txn in all_txns:
        oid = txn.get("orderId", "N/A")
        grp = orders.setdefault(oid, {
            "line_item_id":             None,
            "sale_amount":              None,
            "sale_date":                None,
            "sale_final_fee":           None,
            "sale_fixed_fee":           None,
            "sale_intl_fee":            None,
            "shipping_label_amount":    0.0,
            "refund_amount":            None,
            "refund_final_fee":         None,
            "refund_fixed_fee":         None,
            "dispute_amount":           None,
            "credit_amount":            None,
        })

        ttype = txn.get("transactionType", "").upper()
        date  = txn.get("transactionDate", "")
        amt   = float(txn.get("amount", {}).get("value", 0.0))
        li    = txn.get("orderLineItems", [{}])[0].get("lineItemId", None)
        fees  = txn.get("orderLineItems", [{}])[0].get("marketplaceFees", [])

        # SALE: capture *one* line_item_id, amount, date, and fees
        if ttype == "SALE" and grp["sale_amount"] is None:
            grp["line_item_id"]   = li
            grp["sale_amount"]    = amt
            grp["sale_date"]      = date
            for f in fees:
                ftype = f.get("feeType", "")
                fval  = float(f.get("amount", {}).get("value", 0.0))
                if   ftype == "FINAL_VALUE_FEE":
                    grp["sale_final_fee"] = fval
                elif ftype == "FINAL_VALUE_FEE_FIXED_PER_ORDER":
                    grp["sale_fixed_fee"] = fval
                elif ftype == "INTERNATIONAL_FEE":
                    grp["sale_intl_fee"]  = fval

        # SHIPPING_LABEL: sum them all
        elif ttype == "SHIPPING_LABEL":
            grp["shipping_label_amount"] += amt

        # REFUND: capture *one* refund amount + fees
        elif ttype == "REFUND" and grp["refund_amount"] is None:
            grp["refund_amount"] = amt
            for f in fees:
                ftype = f.get("feeType", "")
                fval  = float(f.get("amount", {}).get("value", 0.0))
                if   ftype == "FINAL_VALUE_FEE":
                    grp["refund_final_fee"] = fval
                elif ftype == "FINAL_VALUE_FEE_FIXED_PER_ORDER":
                    grp["refund_fixed_fee"] = fval

        # DISPUTE: capture *one* dispute
        elif ttype == "DISPUTE" and grp["dispute_amount"] is None:
            grp["dispute_amount"] = amt

        # CREDIT: capture *one* credit
        elif ttype == "CREDIT" and grp["credit_amount"] is None:
            grp["credit_amount"] = amt

    # 3) Create (if needed) the grouped table with REAL for numeric columns
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions_grouped (
        order_id                     TEXT    PRIMARY KEY,
        line_item_id                 TEXT,
        sale_amount                  REAL,
        sale_transaction_date        TEXT,
        sale_final_value_fee         REAL,
        sale_fixed_final_value_fee   REAL,
        sale_international_fee       REAL,
        shipping_label_amount        REAL,
        refund_amount                REAL,
        refund_final_value_fee       REAL,
        refund_fixed_final_value_fee REAL,
        dispute_amount               REAL,
        credit_amount                REAL
    );
    """)
    cursor.execute("DELETE FROM transactions_grouped;")

    # 4) Insert one row per order
    for oid, grp in orders.items():
        cursor.execute("""
        INSERT OR REPLACE INTO transactions_grouped (
           order_id, line_item_id, sale_amount, sale_transaction_date,
           sale_final_value_fee, sale_fixed_final_value_fee, sale_international_fee,
           shipping_label_amount, refund_amount, refund_final_value_fee,
           refund_fixed_final_value_fee, dispute_amount, credit_amount
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            oid,
            grp["line_item_id"],
            grp["sale_amount"],
            grp["sale_date"],
            grp["sale_final_fee"],
            grp["sale_fixed_fee"],
            grp["sale_intl_fee"],
            grp["shipping_label_amount"],
            grp["refund_amount"],
            grp["refund_final_fee"],
            grp["refund_fixed_fee"],
            grp["dispute_amount"],
            grp["credit_amount"],
        ))
    cursor.connection.commit()
    print(f"Inserted {len(orders)} grouped orders into 'transactions_grouped'.")


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
        <DetailLevel>ReturnAll</DetailLevel>
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
        <OutputSelector>
        SoldList.OrderTransactionArray.OrderTransaction
        .Order.TransactionArray.Transaction
        .Item.PictureDetails.GalleryURL
        </OutputSelector>
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
        pic_url = None
        pic_det = item.find("PictureDetails")
        if pic_det:
            gallery = pic_det.find("GalleryURL")
            if gallery and gallery.text:
                pic_url = gallery.text

        photo_url = pic_url or "N/A"
        list_date = item.find("StartTime").text if item and item.find("StartTime") else "N/A"
        sold_date = item.find("EndTime").text if item and item.find("EndTime") else "N/A"
        if list_date != "N/A" and sold_date != "N/A":
            list_dt = datetime.strptime(list_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            sold_dt = datetime.strptime(sold_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            time_to_sell = (sold_dt - list_dt).days
        else:
            time_to_sell = None
        sku = item.find("SKU").text if item and item.find("SKU") else None
        quant_sold = item.find("QuantitySold").text if item and item.find("QuantitySold") else None
        sold_for_price = transaction.find("TransactionPrice").text if transaction.find("TransactionPrice") else None
        shipping_paid = item.find("ShippingServiceCost").text if item and item.find("ShippingServiceCost") else None
        
        fixed_final_fee = None
        final_fee = None
        international_fee = None
        cost_to_ship = None
        refund_to_buyer = None
        refund_owed = None
        refund_to_seller = None
        
        cursor.execute("""
        INSERT INTO sold_items (
          order_id, transaction_id, item_id, item_title, photo_url,
          list_date, sold_date, time_to_sell, sku, quantity_sold,
          sold_for_price, shipping_paid, final_fee, fixed_final_fee,
          international_fee, cost_to_ship, refund_to_buyer,
          refund_owed, refund_to_seller
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(order_id, transaction_id) DO UPDATE SET
          item_id            = excluded.item_id,
          item_title         = excluded.item_title,
          photo_url          = excluded.photo_url,
          list_date          = excluded.list_date,
          sold_date          = excluded.sold_date,
          time_to_sell       = excluded.time_to_sell,
          sku                = excluded.sku,
          quantity_sold      = excluded.quantity_sold,
          sold_for_price     = excluded.sold_for_price,
          shipping_paid      = excluded.shipping_paid,
          final_fee          = excluded.final_fee,
          fixed_final_fee    = excluded.fixed_final_fee,
          international_fee  = excluded.international_fee,
          cost_to_ship       = excluded.cost_to_ship,
          refund_to_buyer    = excluded.refund_to_buyer,
          refund_owed        = excluded.refund_owed,
          refund_to_seller   = excluded.refund_to_seller;
        """, (
          order_id, transaction_id, item_id, item_title, photo_url,
          list_date, sold_date, time_to_sell, sku, quant_sold,
          sold_for_price, shipping_paid, final_fee, fixed_final_fee,
          international_fee, cost_to_ship, refund_to_buyer,
          refund_owed, refund_to_seller
        ))
    
    cursor.connection.commit()
    print("Sold items data upserted (manual fields preserved).")

def update_sold_data(cursor):
    """
    Update sold items data with financial details from transactions_grouped.
    """
    update_query = '''
    UPDATE sold_items
    SET
        final_fee = (
            SELECT tg.sale_final_value_fee
            FROM transactions_grouped AS tg
            WHERE tg.line_item_id = sold_items.transaction_id
        ),
        fixed_final_fee = (
            SELECT tg.sale_fixed_final_value_fee
            FROM transactions_grouped AS tg
            WHERE tg.line_item_id = sold_items.transaction_id
        ),
        international_fee = (
            SELECT tg.sale_international_fee
            FROM transactions_grouped AS tg
            WHERE tg.line_item_id = sold_items.transaction_id
        ),
        cost_to_ship = (
            SELECT tg.shipping_label_amount
            FROM transactions_grouped AS tg
            WHERE tg.line_item_id = sold_items.transaction_id
        ),
        refund_owed = (
            SELECT tg.refund_amount
            FROM transactions_grouped AS tg
            WHERE tg.line_item_id = sold_items.transaction_id
        ),
        refund_to_seller = (
            SELECT (tg.refund_final_value_fee + tg.refund_fixed_final_value_fee)
            FROM transactions_grouped AS tg
            WHERE tg.line_item_id = sold_items.transaction_id
        )
    WHERE EXISTS (
        SELECT 1
        FROM transactions_grouped AS tg
        WHERE tg.line_item_id = sold_items.transaction_id
    );
    '''
    cursor.execute(update_query)
    cursor.connection.commit()
    print("Sold items updated with financial data from transactions_grouped.")


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
        get_inventory_data(cursor, access_token)
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
        cursor.execute("SELECT * FROM sold_items ORDER BY sold_date DESC")
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
    return jsonify(data)

@app.route('/api/sold-items/<order_id>', methods=['PATCH'])
def update_sold_item(order_id):
    data = request.get_json() or {}
    allowed_fields = {
        "item_cost", "purchased_at", "net_return", "roi", "net_profit_margin"
        # add any other fields you want editable
    }
    updates = {k: data[k] for k in data if k in allowed_fields}
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    set_clause = ", ".join(f"{field}=?" for field in updates)
    values = list(updates.values()) + [order_id]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE sold_items SET {set_clause} WHERE order_id=?",
        values
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "updated"})

if __name__ == '__main__':
    # Run your Flask application in debug mode during development
    app.run(debug=True)
