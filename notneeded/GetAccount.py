import requests
import config
import csv
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# eBay Trading API endpoint
EBAY_API_URL = "https://api.ebay.com/ws/api.dll"

# eBay headers
HEADERS = {
    "X-EBAY-API-COMPATIBILITY-LEVEL": "967",  # Use the latest version
    "X-EBAY-API-DEV-NAME": config.EBAY_DEV_ID,
    "X-EBAY-API-APP-NAME": config.EBAY_APP_ID,
    "X-EBAY-API-CERT-NAME": config.EBAY_CERT_ID,
    "X-EBAY-API-CALL-NAME": "GetAccount",
    "X-EBAY-API-SITEID": "0",  # 0 for US
    "Content-Type": "text/xml"
}

def get_account_entries():
    account_entries = []
    page_number = 1
    has_more_pages = True
    utc = timezone.utc

    while has_more_pages:
        # XML payload for GetAccount
        XML_PAYLOAD = f"""<?xml version="1.0" encoding="utf-8"?>
<GetAccountRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{config.ACCESS_TOKEN}</eBayAuthToken>
    </RequesterCredentials>
    <AccountEntrySortType>AccountEntryCreatedTimeAscending</AccountEntrySortType>
    <Pagination>
        <EntriesPerPage>200</EntriesPerPage>
        <PageNumber>{page_number}</PageNumber>
    </Pagination>
    <ViewType>Invoice</ViewType>
    <BeginDate>{(datetime.now(utc) - timedelta(days=20)).strftime('%Y-%m-%dT%H:%M:%S.000Z')}</BeginDate>
    <EndDate>{datetime.now(utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')}</EndDate>
</GetAccountRequest>"""

        # Make the request
        response = requests.post(EBAY_API_URL, headers=HEADERS, data=XML_PAYLOAD)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "xml")
            entries = soup.find_all("AccountEntry")

            for entry in entries:
                order_id = entry.find("").text if entry.find("") else "N/A"
                item_id = entry.find("ItemID").text if entry.find("ItemID") else "N/A"
                title = entry.find("Title").text if entry.find("Title") else "N/A"
                date = entry.find("Date").text if entry.find("Date") else "N/A"
                
                entry_type = entry.find("AccountDetailsEntryType").text if entry.find("AccountDetailsEntryType") else "N/A"
                description = entry.find("Description").text if entry.find("Description") else "N/A"
                gross_amount = entry.find("GrossDetailAmount").text if entry.find("GrossDetailAmount") else "N/A"
                net_amount = entry.find("NetDetailAmount").text if entry.find("NetDetailAmount") else "N/A"
                balance = entry.find("Balance").text if entry.find("Balance") else "N/A"
                memo = entry.find("Memo").text if entry.find("Memo") else "N/A"
               
                transaction_id = entry.find("TransactionID").text if entry.find("TransactionID") else "N/A"
                reference_id = entry.find("ReferenceID").text if entry.find("ReferenceID") else "N/A"

                account_entries.append([
                    date, title, entry_type, description, gross_amount, net_amount,
                    balance, memo, item_id, transaction_id, reference_id
                ])

            # Check if there are more pages
            has_more_tag = soup.find("HasMoreEntries")
            has_more_pages = has_more_tag and has_more_tag.text.lower() == "true"
            page_number += 1
        else:
            print("Error:", response.status_code, response.text)
            break

    return account_entries

# Fetch account entries
entries = get_account_entries()

# Write data to CSV file
csv_file = "ebay_account_entries1.csv"
with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow([
        "Date", "Title", "Entry Type", "Description", "Gross Amount", "Net Amount",
        "Balance", "Memo", "ItemID", "TransactionID", "ReferenceID"
    ])
    writer.writerows(entries)

print(f"Successfully saved to {csv_file}")