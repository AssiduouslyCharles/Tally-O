import os
from dotenv import load_dotenv
import base64
import requests
from urllib.parse import urlencode
from flask import Flask, jsonify, render_template, redirect, request, session, url_for

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)

# Use a strong random value for the secret key, or load it from a secure file/environment variable
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

# eBay API credentials (ensure these are set in your environment)
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

# Route for the home page (frontend will eventually be served here or separately)
@app.route('/')
def index():
    # Initially serve a basic HTML template. Create the templates folder and index.html inside it.
    return render_template('index.html')

# A simple test REST endpoint
@app.route('/api/test')
def test_api():
    return jsonify({"message": "Hello, world!"})

@app.route('/auth/ebay/login')
def ebay_login():
    # Create a dictionary of parameters for the OAuth URL
    params = {
        "client_id": EBAY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": EBAY_REDIRECT_URI,
        "scope": EBAY_SCOPES,
    }
    # Use urlencode to safely encode the query parameters
    query_string = urlencode(params)
    auth_url = f"{EBAY_OAUTH_URL}?{query_string}"
    
    # For troubleshooting: log the constructed URL to the console
    #print("Constructed OAuth URL:", auth_url)
    
    # For debugging purposes, return the URL as plain text so you can inspect it in your browser.
    # Once you verify it, comment out the return below and uncomment the redirect.
    #return auth_url
    
    # When debugging is complete, switch back to redirecting:
    return redirect(auth_url)

@app.route('/auth/ebay/callback')
def ebay_callback():
    # Retrieve the authorization code from the URL parameters
    code = request.args.get('code')
    if not code:
        return "Error: Missing authorization code.", 400

    # eBay requires Basic authentication with your client ID and client secret.
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

    # Store tokens in the session (for demonstration; consider a persistent storage in production)
    session['access_token'] = token_data.get('access_token')
    session['refresh_token'] = token_data.get('refresh_token')

    # After successful login, redirect to a dashboard or home page
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('ebay_login'))
    # You could now use the access token to request user data from eBay and display it
    return render_template('dashboard.html', token=access_token)

if __name__ == '__main__':
    # Debug mode is helpful during development
    app.run(debug=True)