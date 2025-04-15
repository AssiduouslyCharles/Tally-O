import os
from dotenv import load_dotenv
import base64
import requests
from urllib.parse import urlencode
from flask import Flask, jsonify, render_template, redirect, request, session, url_for
from datetime import timedelta

# Determine the directory where this file is located
basedir = os.path.abspath(os.path.dirname(__file__))
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
    SESSION_COOKIE_HTTPONLY=True,     # Disallow JavaScript to access the cookie
    SESSION_COOKIE_SAMESITE='Lax',      # Helps mitigate CSRF attacks
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30)  # Set session lifetime as needed
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

if __name__ == '__main__':
    # Run your Flask application in debug mode during development
    app.run(debug=True)
