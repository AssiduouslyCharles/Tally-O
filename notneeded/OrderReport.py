import requests
import time
import config
import gzip
import io
import zipfile

# eBay Sell Feed API base URL
EBAY_API_URL = "https://api.ebay.com/sell/feed/v1"

# Standard headers for creating tasks and checking status.
HEADERS = {
    "Authorization": f"Bearer {config.ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Step 1: Create the order task
def request_order_report():
    url = f"{EBAY_API_URL}/order_task"
    payload = {
        "feedType": "LMS_ORDER_REPORT",
        "filterCriteria": {
            "dateRange": {
                "startDate": "2024-01-01T00:00:00.000Z",
                "endDate": "2024-12-31T23:59:59.999Z"
            }
        },
        "schemaVersion": "1113"
    }
    
    response = requests.post(url, headers=HEADERS, json=payload)
    
    if response.status_code in [200, 201, 202]:
        try:
            json_response = response.json()
        except ValueError:
            json_response = None
        
        if json_response:
            task_id = json_response.get("taskId")
            print(f"Report request successful! Task ID: {task_id}")
            return task_id
        else:
            # If the response body is empty, check the Location header
            location = response.headers.get("Location")
            if location:
                task_id = location.rstrip('/').split('/')[-1]
                print(f"Report request successful! Task ID (from header): {task_id}")
                return task_id
            else:
                print("Response is empty and no task location provided.")
                return None
    else:
        print("Error requesting report:", response.status_code, response.text)
        return None

# Step 2: Check the status of the order task
def check_report_status(task_id):
    url = f"{EBAY_API_URL}/order_task/{task_id}"
    
    while True:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            json_data = response.json()
            report_status = json_data.get("status")
            print(f"Report Status: {report_status}")
            
            if report_status in ["COMPLETED", "COMPLETED_WITH_ERROR"]:
                return task_id
        else:
            print("Error checking report status:", response.status_code, response.text)
        
        print("Waiting for report to be ready...")
        time.sleep(30)  # Wait before checking again

# Step 3: Download the report using the getResultFile method and the order task ID,
# and decompress it if necessary.
def download_report(task_id):
    # Use the getResultFile endpoint as per documentation:
    # GET https://api.ebay.com/sell/feed/v1/task/{task_id}/download_result_file
    url = f"{EBAY_API_URL}/task/{task_id}/download_result_file"
    download_headers = {
        "Authorization": f"Bearer {config.ACCESS_TOKEN}",
        "Accept": "*/*"
    }
    
    response = requests.get(url, headers=download_headers)
    
    if response.status_code == 200:
        content = response.content

        # Debug: Print the first 100 bytes of the file in hexadecimal
        print("First 100 bytes of downloaded file:", content[:100].hex())
        
        # Check if content is gzip-compressed (starts with 0x1f 0x8b)
        if content.startswith(b'\x1f\x8b'):
            print("Gzip compressed file detected. Decompressing...")
            with gzip.GzipFile(fileobj=io.BytesIO(content)) as gz:
                content = gz.read()
        # Check if content is a ZIP archive (starts with "PK\x03\x04")
        elif content.startswith(b'PK\x03\x04'):
            print("ZIP compressed file detected. Decompressing...")
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                namelist = zf.namelist()
                print("ZIP archive contains:", namelist)
                # Assume the first file in the archive is the report
                content = zf.read(namelist[0])
        
        # Decide on a file extension based on the content.
        # If content (after decompression) starts with '<?xml', we assume XML.
        if content.lstrip().startswith(b'<?xml'):
            report_filename = "ebay_order_report2.xml"
        else:
            report_filename = "ebay_order_report2.csv"
        
        with open(report_filename, "wb") as file:
            file.write(content)
        print(f"Report downloaded successfully: {report_filename}")
    else:
        print("Error downloading report:", response.status_code, response.text)

# Run the complete process
if __name__ == "__main__":
    task_id = request_order_report()
    if task_id:
        task_id = check_report_status(task_id)
        if task_id:
            download_report(task_id)