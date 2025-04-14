import requests
import config
import csv
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, UTC

# eBay Trading API endpoint
EBAY_API_URL = "https://api.ebay.com/ws/api.dll"

# eBay headers
HEADERS = {
    "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
    "X-EBAY-API-DEV-NAME": config.EBAY_DEV_ID,
    "X-EBAY-API-APP-NAME": config.EBAY_APP_ID,
    "X-EBAY-API-CERT-NAME": config.EBAY_CERT_ID,
    "X-EBAY-API-CALL-NAME": "GetOrders",
    "X-EBAY-API-SITEID": "0",
    "Content-Type": "text/xml"
}

# Function to create XML payload
def create_xml_payload(page_number):
    return f"""<?xml version="1.0" encoding="utf-8"?>
    <GetOrdersRequest xmlns="urn:ebay:apis:eBLBaseComponents">
        <RequesterCredentials>
            <eBayAuthToken>{config.ACCESS_TOKEN}</eBayAuthToken>
        </RequesterCredentials>
        <CreateTimeFrom>{(datetime.now(UTC) - timedelta(days=90)).strftime('%Y-%m-%dT%H:%M:%S.000Z')}</CreateTimeFrom>
        <CreateTimeTo>{datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S.000Z')}</CreateTimeTo>
        <Pagination>
            <EntriesPerPage>100</EntriesPerPage>
            <PageNumber>{page_number}</PageNumber>
        </Pagination>
        <OrderRole>Seller</OrderRole>
        <OrderStatus>All</OrderStatus>
    </GetOrdersRequest>"""

# Initialize variables
orders = []
page_number = 1
entries_per_page = 100

while True:
    # Create XML payload for the current page
    xml_payload = create_xml_payload(page_number)

    # Make the API request
    response = requests.post(EBAY_API_URL, headers=HEADERS, data=xml_payload)

    if response.status_code == 200:
        # Parse XML response using BeautifulSoup
        soup = BeautifulSoup(response.text, "xml")

        # Extract orders
        current_orders = soup.find_all("Order")

        if not current_orders:
            break

        for order in current_orders:
            order_id = order.OrderID.text if order.OrderID else "N/A"
            buyer_user_id = order.BuyerUserID.text if order.BuyerUserID else "N/A"
            total = order.Total.text if order.Total else "N/A"
            created_time = order.CreatedTime.text if order.CreatedTime else "N/A"
            status = order.OrderStatus.text if order.OrderStatus else "N/A"

            orders.append([order_id, buyer_user_id, total, created_time, status])

        # Check if more pages are available
        total_pages = int(soup.TotalNumberOfPages.text) if soup.TotalNumberOfPages else 1
        if page_number >= total_pages:
            break

        page_number += 1
    else:
        print(f"Error: {response.status_code} - {response.text}")
        break

# Write data to CSV file
csv_file = "ebay_orders.csv"
with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Order ID", "Buyer User ID", "Total", "Created Time", "Status"])
    writer.writerows(orders)

print(f"Successfully saved {len(orders)} orders to {csv_file}")