import requests
import config
import csv
from bs4 import BeautifulSoup
from datetime import datetime

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

# XML payload for GetMyeBaySelling (Fetching Sold Items)
XML_PAYLOAD = f"""<?xml version="1.0" encoding="utf-8"?>
<GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{config.ACCESS_TOKEN}</eBayAuthToken>
    </RequesterCredentials>
    <SoldList>
        <Include>true</Include>
        <Pagination>
            <EntriesPerPage>50</EntriesPerPage>
            <PageNumber>1</PageNumber>
        </Pagination>
    </SoldList>
</GetMyeBaySellingRequest>"""

# Make the request
response = requests.post(EBAY_API_URL, headers=HEADERS, data=XML_PAYLOAD)

# Print response
if response.status_code == 200:
    #Parse response with beautifulsoup
    soup = BeautifulSoup(response.text, "xml")
    
    #Extract Sold Items
    transactions = soup.find_all("Transaction")

    #Prepare data for CSV
    sold_items = []
    for transaction in transactions:
        item = transaction.find("Item")
        order_id = transaction.find("OrderLineItemID").text if transaction.find("OrderLineItemID") else "N/A"
        item_id = item.find("ItemID").text if item.find("ItemID") else "N/A"
        item_title = item.find("Title").text if item.find("Title") else "N/A"
        photo_URL = item.find("PictureDetails").text if item.find("PictureDetails") else "N/A"
        list_date = item.find("StartTime").text if item.find("StartTime") else "N/A"
        sold_date = item.find("EndTime").text if item.find("EndTime") else "N/A"
        # Convert date strings to datetime objects
        if list_date != "N/A" and sold_date != "N/A":
            list_dt = datetime.strptime(list_date, "%Y-%m-%dT%H:%M:%S.%fZ")  # Example format
            sold_dt = datetime.strptime(sold_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            time_to_sell = (sold_dt - list_dt).days  # Get difference in days
        else:
            time_to_sell = "N/A"
        item_cost = ""
        purchased_at = ""
        sku = item.find("SKU").text if item.find("SKU") else ""
        quant_sold = item.find("QuantitySold").text if item.find("QuantitySold") else "N/A"
        sold_for_price = transaction.find("TransactionPrice").text if item.find("TransactionPrice") else "N/A"
        shipping_paid = item.find("ShippingServiceCost").text if item.find("ShippingServiceCost") else "N/A"
        #fixed_final_fee = ""
        #final_fee = ""
        #international_fee = ""
        #cost_to_ship = ""
        #net_return = (sold_for_price + shipping_paid) - (fixed_final_fee + final_fee + international_fee + cost_to_ship + item_cost)
        #roi = net_return/item_cost
        #net_profit_margin = net_return/(sold_for_price + shipping_paid)
        #refund_to_buyer = ""
        #refund_owed = ""
        #refund_to_seller = ""
        #Append to list
        sold_items.append([order_id, item_id, item_title, photo_URL, list_date, sold_date, time_to_sell, item_cost, purchased_at, sku, quant_sold, sold_for_price, shipping_paid])

    #Write data to CSV file
    csv_file = "sold_list.csv"
    with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Order ID", "Item ID", "Title", "Photo URL", "List Date", "Sold Date", "Time To Sell", "Item Cost", "Purchased At", "SKU", "Quantity Sold", "Sold For Price", "Shipping Paid"])
        writer.writerows(sold_items)

    print(f"Successfully saved to {csv_file}")

else:
    print("Error:", response.status_code, response.text)