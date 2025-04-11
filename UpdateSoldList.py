import csv

# Filenames for the two CSV files:
sold_list_file = "sold_list.csv"                # Sold list CSV (from GetMyeBaySelling)
transactions_file = "ebay_transactions_grouped.csv"  # eBay transactions CSV (from getTransactions)
output_file = "sold_list_updated.csv"            # Output file with updated data

# Read the transactions CSV into a dictionary keyed on the "Line Item ID".
# In case there are multiple line item IDs separated by semicolons,
# we will map each individual ID to the entire row.
transactions_dict = {}
with open(transactions_file, mode="r", newline="", encoding="utf-8") as tf:
    reader = csv.DictReader(tf)
    for row in reader:
        line_item_ids_str = row.get("Line Item IDs", "")
        if line_item_ids_str:
            # Split by semicolon and strip each part.
            for part in [p.strip() for p in line_item_ids_str.split(";")]:
                if part:
                    transactions_dict[part] = row

# Read the sold list CSV into a list of dictionaries.
sold_list_rows = []
with open(sold_list_file, mode="r", newline="", encoding="utf-8") as sf:
    reader = csv.DictReader(sf)
    sold_list_fieldnames = reader.fieldnames[:]  # copy original header list
    for row in reader:
        sold_list_rows.append(row)

# Define the new columns to update (or add) in the sold list CSV.
# (These names can be adjusted to match what you desire.)
new_columns = [
    "Final Fee", 
    "Fixed Final Fee", 
    "International Fee", 
    "Cost To Ship", 
    "Refund Owed", 
    "Refund To Seller"
]
# Make sure all new columns are in the fieldnames.
for col in new_columns:
    if col not in sold_list_fieldnames:
        sold_list_fieldnames.append(col)

# Process each sold list row:
# Match the sold list "Transaction ID" with the transactions CSV's "Line Item ID"
# and fill in the missing corresponding fields.
for row in sold_list_rows:
    transaction_id = row.get("Transaction ID", "").strip()
    matched = None
    if transaction_id:
        # Try to match with a key in transactions_dict.
        if transaction_id in transactions_dict:
            matched = transactions_dict[transaction_id]
    if matched:
        # Update the sold list row with data from the transactions CSV.
        row["Final Fee"] = matched.get("Final Fee", "")
        row["Fixed Final Fee"] = matched.get("Fixed Final Fee", "")
        row["International Fee"] = matched.get("International Fee", "")
        row["Cost To Ship"] = matched.get("Cost To Ship", "")
        row["Refund Owed"] = matched.get("Refund Owed", "")
        # Calculate "Refund To Seller" = Refund Final Fee + Refund Fixed Final Fee
        try:
            refund_final = float(matched.get("Refund Final Fee", "0") or "0")
            refund_fixed = float(matched.get("Refund Fixed Final Fee", "0") or "0")
            refund_to_seller = refund_final + refund_fixed
            row["Refund To Seller"] = f"{refund_to_seller:.2f}"
        except Exception:
            row["Refund To Seller"] = ""
    else:
        # If no match was found, leave the new columns blank.
        for col in new_columns:
            row[col] = ""

# Write the updated sold list CSV (this will overwrite any previous version of output_file).
with open(output_file, mode="w", newline="", encoding="utf-8") as outf:
    writer = csv.DictWriter(outf, fieldnames=sold_list_fieldnames)
    writer.writeheader()
    for row in sold_list_rows:
        writer.writerow(row)

print(f"Updated sold list CSV written to {output_file}")