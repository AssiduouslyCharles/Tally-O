import requests
import config
import csv
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# eBay Trading API endpoint
EBAY_API_URL = "https://api.ebay.com/ws/api.dll"

# eBay headers
HEADERS = {
    "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
    "X-EBAY-API-DEV-NAME": config.EBAY_DEV_ID,
    "X-EBAY-API-APP-NAME": config.EBAY_APP_ID,
    "X-EBAY-API-CERT-NAME": config.EBAY_CERT_ID,
    "X-EBAY-API-CALL-NAME": "GetMyeBaySelling",
    "X-EBAY-API-SITEID": "0",
    "Content-Type": "text/xml"
}

# Set the date range (6 months ago to today)
from datetime import datetime, timedelta, timezone

mod_time_from = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
mod_time_to = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

# Initialize variables for pagination
page_number = 1
entries_per_page = 200  # Maximum allowed
sold_items = []

while True:
    # XML payload with custom date range
    XML_PAYLOAD = f"""<?xml version="1.0" encoding="utf-8"?>
    <GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
        <RequesterCredentials>
            <eBayAuthToken>{config.ACCESS_TOKEN}</eBayAuthToken>
        </RequesterCredentials>
        <SoldList>
            <Include>true</Include>
        </SoldList>
    </GetMyeBaySellingRequest>"""

    # Make the request
    response = requests.post(EBAY_API_URL, headers=HEADERS, data=XML_PAYLOAD)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "xml")
        
        # Check if there are more items to fetch
        has_more_items = soup.find("HasMoreItems").text.lower() == "true" if soup.find("HasMoreItems") else False

        # Extract transactions
        transactions = soup.find_all("Transaction")

        for transaction in transactions:
            item = transaction.find("Item")
            order_id = transaction.find("OrderLineItemID").text if transaction.find("OrderLineItemID") else "N/A"
            item_id = item.find("ItemID").text if item.find("ItemID") else "N/A"
            item_title = item.find("Title").text if item.find("Title") else "N/A"
            photo_URL = item.find("PictureDetails").text if item.find("PictureDetails") else "N/A"
            list_date = item.find("StartTime").text if item.find("StartTime") else "N/A"
            sold_date = item.find("EndTime").text if item.find("EndTime") else "N/A"

            # Calculate time to sell
            if list_date != "N/A" and sold_date != "N/A":
                list_dt = datetime.strptime(list_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                sold_dt = datetime.strptime(sold_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                time_to_sell = (sold_dt - list_dt).days
            else:
                time_to_sell = "N/A"

            sku = item.find("SKU").text if item.find("SKU") else ""
            quant_sold = item.find("QuantitySold").text if item.find("QuantitySold") else "N/A"
            sold_for_price = transaction.find("TransactionPrice").text if transaction.find("TransactionPrice") else "N/A"
            shipping_paid = item.find("ShippingServiceCost").text if item.find("ShippingServiceCost") else "N/A"

            # Append extracted data to list
            sold_items.append([
                order_id, item_id, item_title, photo_URL, list_date, sold_date, time_to_sell, 
                sku, quant_sold, sold_for_price, shipping_paid
            ])

        print(f"Page {page_number} processed with {len(transactions)} transactions.")

        # Break the loop if there are no more items
        if not has_more_items:
            break

        # Move to next page
        page_number += 1
    else:
        print(f"Error on page {page_number}: {response.status_code}, {response.text}")
        break  # Stop if an error occurs

# Write data to CSV
csv_file = "sold_list.csv"
with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Order ID", "Item ID", "Title", "Photo URL", "List Date", "Sold Date", "Time To Sell (days)", "SKU", "Quantity Sold", "Sold For Price", "Shipping Paid"])
    writer.writerows(sold_items)

print(f"Successfully saved {len(sold_items)} records to {csv_file}")