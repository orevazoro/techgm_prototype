import sqlite3
from pathlib import Path

DB_PATH = Path("db/sandbox.db")

def init_sandbox():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        city TEXT NOT NULL,
        tier TEXT NOT NULL,          -- 'gold', 'silver', 'bronze'
        is_deleted INTEGER DEFAULT 0 -- 1 = soft-deleted / test account
    );

    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL
    );

    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        order_date TEXT NOT NULL,    -- YYYY-MM-DD
        status TEXT NOT NULL,        -- 'completed', 'cancelled', 'refunded', 'pending'
        net_amount REAL NOT NULL,    -- actual revenue (excludes tax)
        gross_amount REAL NOT NULL,  -- includes 18% GST
        is_deleted INTEGER DEFAULT 0,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );
    """)

    customers = [
        (1, "Aarav Sharma", "Mumbai", "gold", 0),
        (2, "Diya Patel", "Ahmedabad", "silver", 0),
        (3, "Rohan Verma", "Bengaluru", "gold", 0),
        (4, "Meera Nair", "Kochi", "bronze", 0),
        (5, "Test Account", "Delhi", "gold", 1), # Soft-deleted test user
    ]
    cur.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?)", customers)

    products = [
        (101, "Mechanical Keyboard", "Electronics", 4500.0),
        (102, "USB-C Hub", "Electronics", 1500.0),
        (103, "Desk Lamp", "Home", 1200.0),
        (104, "Ergonomic Chair", "Furniture", 12000.0),
    ]
    cur.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", products)

    orders = [
        (1001, 1, 101, "2026-10-05", "completed", 4500.0, 5310.0, 0),
        (1002, 2, 102, "2026-10-08", "completed", 1500.0, 1770.0, 0),
        (1003, 3, 104, "2026-10-12", "cancelled", 12000.0, 14160.0, 0),
        (1004, 1, 103, "2026-10-15", "refunded", 1200.0, 1416.0, 0),
        (1005, 4, 102, "2026-10-18", "completed", 1500.0, 1770.0, 0),
        (1006, 3, 101, "2026-10-20", "pending", 4500.0, 5310.0, 0),
        (1007, 5, 104, "2026-10-22", "completed", 12000.0, 14160.0, 1), # Soft-deleted test order
        (1008, 1, 104, "2026-11-02", "completed", 12000.0, 14160.0, 0),
    ]
    cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)", orders)

    conn.commit()
    conn.close()
    print(f"Sandbox database created at {DB_PATH}")

if __name__ == "__main__":
    init_sandbox()