import requests
import config
import csv
from bs4 import BeautifulSoup

# eBay Trading API endpoint
EBAY_API_URL = "https://api.ebay.com/ws/api.dll"  # Use sandbox URL for testing: https://api.sandbox.ebay.com/ws/api.dll

# eBay headers
HEADERS = {
    "X-EBAY-API-COMPATIBILITY-LEVEL": "967",  # Use the latest version
    "X-EBAY-API-DEV-NAME": config.EBAY_DEV_ID,
    "X-EBAY-API-APP-NAME": config.EBAY_APP_ID,
    "X-EBAY-API-CERT-NAME": config.EBAY_CERT_ID,
    "X-EBAY-API-CALL-NAME": "GetMyeBaySelling",
    "X-EBAY-API-SITEID": "0",  # 0 for US, change for other regions
    "Content-Type": "text/xml"
}

# XML payload for GetMyeBaySelling
XML_PAYLOAD = f"""<?xml version="1.0" encoding="utf-8"?>
<GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{config.ACCESS_TOKEN}</eBayAuthToken>
    </RequesterCredentials>
    <ActiveList>
        <Include>true</Include>
        <Pagination>
            <EntriesPerPage>200</EntriesPerPage>
            <PageNumber>1</PageNumber>
        </Pagination>
    </ActiveList>
</GetMyeBaySellingRequest>"""

# Make the request
response = requests.post(EBAY_API_URL, headers=HEADERS, data=XML_PAYLOAD)

# Print response
if response.status_code == 200:
    #Parse xml response using BeautifulSoup
    soup = BeautifulSoup(response.text, "xml")

    #Extract active listings
    items = soup.find_all("Item")

    #Prepare data for CSV
    active_listings = []
    for item in items:
        item_id = item.find("ItemID").text if item.find("ItemID") else "N/A"
        item_title = item.find("Title").text if item.find("Title") else "N/A"
        photo_URL = item.find("PictureDetails").text if item.find("PictureDetails") else "N/A"
        list_price = item.find("CurrentPrice").text if item.find("CurrentPrice") else "N/A"
        list_date = item.find("StartTime").text if item.find("StartTime") else "N/A"
        item_cost = ""
        avail_quant = item.find("QuantityAvailable").text if item.find("QuantityAvailable") else "N/A"
        purchased_at = ""
        sku = item.find("SKU").text if item.find("SKU") else ""

        #Append to List
        active_listings.append([item_id, item_title, photo_URL, list_price, list_date, item_cost, avail_quant, purchased_at, sku])

    #Write data to CSV file
    csv_file = "active_listings.csv"
    with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Item ID", "Item Title", "Product Photo URL", "List Price", "List Date", "Item Cost", "Available Quantity", "Purchased At", "SKU"])
        writer.writerows(active_listings)

    print(f"Data successfully saved to {csv_file}")

else:
    print("Error:", response.status_code, response.text)