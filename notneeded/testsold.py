import requests
import config

# eBay Trading API endpoint – use sandbox URL for testing if needed
EBAY_API_URL = "https://api.ebay.com/ws/api.dll"

# eBay headers
HEADERS = {
    "X-EBAY-API-COMPATIBILITY-LEVEL": "967",  # Use the latest version
    "X-EBAY-API-DEV-NAME": config.EBAY_DEV_ID,
    "X-EBAY-API-APP-NAME": config.EBAY_APP_ID,
    "X-EBAY-API-CERT-NAME": config.EBAY_CERT_ID,
    "X-EBAY-API-CALL-NAME": "GetMyeBaySelling",
    "X-EBAY-API-SITEID": "0",  # 0 for US
    "Content-Type": "text/xml"
}

# XML payload for GetMyeBaySelling (Fetching Sold Items with full detail including order grouping)
XML_PAYLOAD = f"""<?xml version="1.0" encoding="utf-8"?>
<GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{config.ACCESS_TOKEN}</eBayAuthToken>
    </RequesterCredentials>
    <SoldList>
        <Include>true</Include>
        <DurationInDays>60</DurationInDays>
        <Pagination>
            <EntriesPerPage>15</EntriesPerPage>
            <PageNumber>3</PageNumber>
        </Pagination>
    </SoldList>
</GetMyeBaySellingRequest>"""

# Make the request
response = requests.post(EBAY_API_URL, headers=HEADERS, data=XML_PAYLOAD)

if response.status_code == 200:
    print(response.text)
else:
    print("Error:", response.status_code, response.text)