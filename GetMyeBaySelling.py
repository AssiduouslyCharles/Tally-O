import requests
import config

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
            <EntriesPerPage>10</EntriesPerPage>
            <PageNumber>1</PageNumber>
        </Pagination>
    </ActiveList>
</GetMyeBaySellingRequest>"""

# Make the request
response = requests.post(EBAY_API_URL, headers=HEADERS, data=XML_PAYLOAD)

# Print response
if response.status_code == 200:
    print(response.text)
else:
    print("Error:", response.status_code, response.text)