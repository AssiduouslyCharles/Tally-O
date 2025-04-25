-- Create the transactions table.
-- Note: The composite PRIMARY KEY ensures uniqueness based on order_id, line_item_id,
-- transaction_type, and transaction_date.
CREATE TABLE IF NOT EXISTS transactions (
    order_id TEXT,
    line_item_id TEXT,
    transaction_type TEXT,
    transaction_date TEXT,
    amount_value REAL,
    sale_final_fee REAL,
    sale_fixed_fee REAL,
    sale_international_fee REAL,
    shipping_label_amount REAL,
    refund_amount REAL,
    refund_final_fee REAL,
    refund_fixed_fee REAL,
    dispute_amount REAL,
    credit_amount REAL,
    PRIMARY KEY (order_id, line_item_id, transaction_type, transaction_date)
);

-- Create the sold_items table.
-- Using order_id as the PRIMARY KEY (ensure that order_id is unique per sold item).
CREATE TABLE IF NOT EXISTS sold_items (
    order_id TEXT,
    transaction_id TEXT,
    item_id TEXT,
    item_title TEXT,
    photo_url TEXT,
    list_date TEXT,
    sold_date TEXT,
    time_to_sell INTEGER,
    item_cost REAL,
    purchased_at TEXT,
    sku TEXT,
    quantity_sold INTEGER,
    sold_for_price REAL,
    shipping_paid REAL,
    final_fee REAL,
    fixed_final_fee REAL,
    international_fee REAL,
    cost_to_ship REAL,
    net_return REAL,
    roi REAL,
    net_profit_margin REAL,
    refund_to_buyer REAL,
    refund_owed REAL,
    refund_to_seller REAL,
    PRIMARY KEY (order_id, transaction_id)
);

CREATE TABLE IF NOT EXISTS transactions_grouped (
    order_id                     TEXT    PRIMARY KEY,
    line_item_id                 TEXT,
    sale_amount                  REAL,
    sale_transaction_date        TEXT,
    sale_final_value_fee         REAL,
    sale_fixed_final_value_fee   REAL,
    sale_international_fee       REAL,
    shipping_label_amount        REAL,
    refund_amount                REAL,
    refund_final_value_fee       REAL,
    refund_fixed_final_value_fee REAL,
    dispute_amount               REAL,
    credit_amount                REAL
);

CREATE TABLE IF NOT EXISTS inventory_items (
    item_id             TEXT    PRIMARY KEY,
    item_title          TEXT,
    photo_url           TEXT,
    list_price          REAL,
    list_date           TEXT,
    item_cost           REAL,
    available_quantity  INTEGER,
    purchased_at        TEXT,
    sku                 TEXT,
    storage_location    TEXT
);