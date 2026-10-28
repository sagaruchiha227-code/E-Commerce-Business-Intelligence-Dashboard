"""
Database layer for E-Commerce BI Dashboard.
Supports SQLite (zero-config local engine) and MySQL (production database).
Provides automated schema creation, rich seed data generation, and migration utilities.
"""

import os
import sqlite3
import random
from datetime import datetime, timedelta

# Default SQLite database path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(PROJECT_DIR, "ecommerce_bi.db")

# Active DB Configuration
CURRENT_CONFIG = {
    "db_type": os.environ.get("BI_DB_TYPE", "sqlite"),  # 'sqlite' or 'mysql'
    "mysql_host": os.environ.get("MYSQL_HOST", "localhost"),
    "mysql_port": int(os.environ.get("MYSQL_PORT", 3306)),
    "mysql_user": os.environ.get("MYSQL_USER", "root"),
    "mysql_password": os.environ.get("MYSQL_PASSWORD", ""),
    "mysql_database": os.environ.get("MYSQL_DATABASE", "ecommerce_bi")
}


def get_connection():
    """Returns an active database connection based on current configuration."""
    if CURRENT_CONFIG["db_type"] == "mysql":
        import mysql.connector
        return mysql.connector.connect(
            host=CURRENT_CONFIG["mysql_host"],
            port=CURRENT_CONFIG["mysql_port"],
            user=CURRENT_CONFIG["mysql_user"],
            password=CURRENT_CONFIG["mysql_password"],
            database=CURRENT_CONFIG["mysql_database"]
        )
    else:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    """Initializes schema in the active database."""
    conn = get_connection()
    cursor = conn.cursor()

    if CURRENT_CONFIG["db_type"] == "mysql":
        # MySQL schema
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) NOT NULL UNIQUE,
            username VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'Executive',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INT PRIMARY KEY AUTO_INCREMENT,
            product_name VARCHAR(255) NOT NULL,
            category VARCHAR(100) NOT NULL
        ) ENGINE=InnoDB;
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INT PRIMARY KEY AUTO_INCREMENT,
            order_date DATE NOT NULL,
            order_status VARCHAR(50) NOT NULL,
            region VARCHAR(100) NOT NULL
        ) ENGINE=InnoDB;
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            item_id INT PRIMARY KEY AUTO_INCREMENT,
            order_id INT NOT NULL,
            product_id INT NOT NULL,
            quantity INT NOT NULL,
            unit_price DECIMAL(10, 2) NOT NULL,
            discount_optional DECIMAL(10, 2) DEFAULT 0.00,
            return_amount_optional DECIMAL(10, 2) DEFAULT 0.00,
            FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        """)
    else:
        # SQLite schema
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'Executive',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_date TEXT NOT NULL,
            order_status TEXT NOT NULL,
            region TEXT NOT NULL
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            discount_optional REAL DEFAULT 0.00,
            return_amount_optional REAL DEFAULT 0.00,
            FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
        );
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(order_status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_region ON orders(region);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_product ON order_items(product_id);")

    conn.commit()
    conn.close()
    seed_default_user()


def create_user(name, email, username, password_hash, role="Executive"):
    """Creates a new user record with hashed password."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if CURRENT_CONFIG["db_type"] == "mysql":
            cursor.execute(
                "INSERT INTO users (name, email, username, password_hash, role) VALUES (%s, %s, %s, %s, %s)",
                (name, email.lower().strip(), username.lower().strip(), password_hash, role)
            )
        else:
            cursor.execute(
                "INSERT INTO users (name, email, username, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                (name, email.lower().strip(), username.lower().strip(), password_hash, role)
            )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return True, user_id
    except Exception as e:
        conn.close()
        err_msg = str(e).lower()
        if "unique" in err_msg or "duplicate" in err_msg:
            if "email" in err_msg:
                return False, "An account with this email address already exists."
            return False, "An account with this username already exists."
        return False, f"Registration failed: {e}"


def get_user_by_email_or_username(identifier):
    """Retrieves user row matching given email or username."""
    if not identifier:
        return None
    ident = identifier.lower().strip()
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT user_id, name, email, username, password_hash, role, created_at FROM users WHERE LOWER(email) = ? OR LOWER(username) = ?"
    if CURRENT_CONFIG["db_type"] == "mysql":
        query = "SELECT user_id, name, email, username, password_hash, role, created_at FROM users WHERE LOWER(email) = %s OR LOWER(username) = %s"

    cursor.execute(query, (ident, ident))
    row = cursor.fetchone()
    conn.close()

    if row:
        if CURRENT_CONFIG["db_type"] == "mysql":
            return {
                "user_id": row[0],
                "name": row[1],
                "email": row[2],
                "username": row[3],
                "password_hash": row[4],
                "role": row[5],
                "created_at": str(row[6])
            }
        else:
            return dict(row)
    return None


def get_user_by_id(user_id):
    """Retrieves user by primary key."""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT user_id, name, email, username, password_hash, role, created_at FROM users WHERE user_id = ?"
    if CURRENT_CONFIG["db_type"] == "mysql":
        query = "SELECT user_id, name, email, username, password_hash, role, created_at FROM users WHERE user_id = %s"

    cursor.execute(query, (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        if CURRENT_CONFIG["db_type"] == "mysql":
            return {
                "user_id": row[0],
                "name": row[1],
                "email": row[2],
                "username": row[3],
                "password_hash": row[4],
                "role": row[5],
                "created_at": str(row[6])
            }
        else:
            return dict(row)
    return None


def seed_default_user():
    """Seeds the initial administrator/executive account if users table is empty."""
    from werkzeug.security import generate_password_hash
    admin = get_user_by_email_or_username("admin@omnistore.bi")
    if not admin:
        hashed = generate_password_hash("Admin123!")
        create_user(
            name="Executive Director",
            email="admin@omnistore.bi",
            username="admin",
            password_hash=hashed,
            role="Executive Director"
        )
        print("Default executive user created: admin@omnistore.bi (Password: Admin123!)")


PRODUCT_CATALOG = [
    # Electronics
    ("UltraBook Pro 15", "Electronics", 1299.99),
    ("Wireless Noise-Canceling Headphones", "Electronics", 249.99),
    ("Curved 4K Gaming Monitor 32-inch", "Electronics", 499.99),
    ("Smart Fitness Watch Series 5", "Electronics", 199.99),
    ("True Wireless Earbuds ANC", "Electronics", 129.99),
    ("Mechanical RGB Gaming Keyboard", "Electronics", 89.99),
    ("High-Speed USB-C GaN Charger 100W", "Electronics", 45.99),
    ("MagSafe 10000mAh Power Bank", "Electronics", 59.99),

    # Apparel & Fashion
    ("Vintage Denim Sherpa Jacket", "Apparel & Fashion", 119.50),
    ("Merino Wool Crewneck Sweater", "Apparel & Fashion", 85.00),
    ("Waterproof Trail Running Shoes", "Apparel & Fashion", 135.00),
    ("Organic Pima Cotton T-Shirt 3-Pack", "Apparel & Fashion", 48.00),
    ("Slim Fit Chino Pants", "Apparel & Fashion", 65.00),
    ("Full-Grain Italian Leather Belt", "Apparel & Fashion", 55.00),
    ("Breathable Athletic Gym Leggings", "Apparel & Fashion", 52.00),

    # Home & Kitchen
    ("Precision Espresso Machine & Grinder", "Home & Kitchen", 649.00),
    ("Digital Air Fryer XXL 6-Quart", "Home & Kitchen", 119.99),
    ("Japanese Damascus Steel Chef Knife Set", "Home & Kitchen", 179.99),
    ("Ergonomic Mesh Executive Chair", "Home & Kitchen", 289.00),
    ("Smart Robotic Vacuum & Mop Combo", "Home & Kitchen", 399.00),
    ("16-Piece Ceramic Matte Dinnerware Set", "Home & Kitchen", 99.50),
    ("Stainless Steel Electric Kettle", "Home & Kitchen", 49.99),

    # Sports & Outdoors
    ("Ultralight 2-Person Backpacking Tent", "Sports & Outdoors", 229.00),
    ("Adjustable Quick-Select Dumbbells 50lb", "Sports & Outdoors", 329.99),
    ("High-Density Eco Yoga Mat & Strap", "Sports & Outdoors", 42.00),
    ("Insulated Stainless Steel Hydration Flask 32oz", "Sports & Outdoors", 34.99),
    ("Hardtail Mountain Bike 29-inch", "Sports & Outdoors", 749.00),
    ("Polarized UV400 Sports Sunglasses", "Sports & Outdoors", 68.00),

    # Beauty & Personal Care
    ("Hyaluronic Acid & Vitamin C Serum", "Beauty & Personal Care", 38.50),
    ("Cold-Pressed Botanical Facial Oil", "Beauty & Personal Care", 46.00),
    ("Sonic Electric Toothbrush Smart UV", "Beauty & Personal Care", 89.99),
    ("Ionic Ceramic Hair Dryer 1800W", "Beauty & Personal Care", 79.99),
    ("Exfoliating Mineral Sea Salt Scrub", "Beauty & Personal Care", 26.00),

    # Books & Stationery
    ("Strategic Executive Leadership Handbook", "Books & Stationery", 29.95),
    ("Hardcover Productivity Daily Planner", "Books & Stationery", 24.50),
    ("Brass Fountain Pen & Archival Ink Set", "Books & Stationery", 62.00),
    ("Artificial Intelligence & Data Architecture", "Books & Stationery", 44.95)
]

REGIONS = ["North America", "Europe", "Asia-Pacific", "Latin America", "Middle East & Africa"]
STATUSES = ["Delivered", "Completed", "Shipped", "Pending", "Cancelled"]
STATUS_WEIGHTS = [0.65, 0.20, 0.05, 0.03, 0.07]  # ~7% cancellation rate baseline


def seed_data(target_orders=2200):
    """Populates realistic BI data spanning 2024 to late 2026."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM products")
    p_count = cursor.fetchone()[0]
    if p_count > 0:
        conn.close()
        return False  # Already seeded

    print(f"Seeding product catalog ({len(PRODUCT_CATALOG)} items)...")
    product_ids = []
    for item in PRODUCT_CATALOG:
        name, category, price = item
        if CURRENT_CONFIG["db_type"] == "mysql":
            cursor.execute("INSERT INTO products (product_name, category) VALUES (%s, %s)", (name, category))
            product_ids.append((cursor.lastrowid, price, category))
        else:
            cursor.execute("INSERT INTO products (product_name, category) VALUES (?, ?)", (name, category))
            product_ids.append((cursor.lastrowid, price, category))

    # Seed orders from 2024-01-01 to 2026-10-25
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2026, 10, 25)
    total_days = (end_date - start_date).days

    random.seed(42)  # Deterministic realistic distribution

    print(f"Generating {target_orders} orders and line items...")
    order_rows = []
    item_rows = []

    for order_idx in range(1, target_orders + 1):
        # Pick date with seasonal weighting (Nov & Dec have holiday spikes, Jan/Feb lower, general upward trend YoY)
        day_offset = random.randint(0, total_days)
        order_date = start_date + timedelta(days=day_offset)

        # Monthly seasonal modifier: November (11) and December (12) get higher order count chance
        if order_date.month in [11, 12]:
            if random.random() < 0.25:
                # Add extra order bias for peak retail season
                day_offset = random.randint(0, total_days)
                order_date = start_date + timedelta(days=day_offset)

        date_str = order_date.strftime("%Y-%m-%d")
        region = random.choice(REGIONS)
        order_status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]

        order_rows.append((order_idx, date_str, order_status, region))

        # 1 to 4 items per order
        num_items = random.choices([1, 2, 3, 4], weights=[0.45, 0.35, 0.15, 0.05])[0]
        selected_products = random.sample(product_ids, num_items)

        for p_id, base_price, category in selected_products:
            qty = random.choices([1, 2, 3, 4, 5], weights=[0.70, 0.18, 0.07, 0.03, 0.02])[0]
            unit_price = round(base_price * random.uniform(0.95, 1.05), 2)
            line_gross = round(qty * unit_price, 2)

            # Discount logic: 35% chance of promotional discount (5% to 25% off)
            discount = 0.00
            if random.random() < 0.35:
                discount_pct = random.choice([0.05, 0.10, 0.15, 0.20, 0.25])
                discount = round(line_gross * discount_pct, 2)

            # Return logic: only for Delivered/Completed orders
            # Return likelihood varies by category (Apparel has higher return rate ~12%, Books low ~2%)
            return_amt = 0.00
            if order_status in ["Delivered", "Completed"]:
                return_prob = 0.04
                if category == "Apparel & Fashion":
                    return_prob = 0.12
                elif category == "Electronics":
                    return_prob = 0.06
                elif category == "Home & Kitchen":
                    return_prob = 0.05

                if random.random() < return_prob:
                    # Partial or full return
                    return_amt = round(line_gross - discount, 2)

            item_rows.append((order_idx, p_id, qty, unit_price, discount, return_amt))

    # Bulk insert
    print(f"Inserting {len(order_rows)} orders...")
    if CURRENT_CONFIG["db_type"] == "mysql":
        cursor.executemany("INSERT INTO orders (order_id, order_date, order_status, region) VALUES (%s, %s, %s, %s)", order_rows)
        cursor.executemany("INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_optional, return_amount_optional) VALUES (%s, %s, %s, %s, %s, %s)", item_rows)
    else:
        cursor.executemany("INSERT INTO orders (order_id, order_date, order_status, region) VALUES (?, ?, ?, ?)", order_rows)
        cursor.executemany("INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_optional, return_amount_optional) VALUES (?, ?, ?, ?, ?, ?)", item_rows)

    conn.commit()
    conn.close()
    print(f"Seeding complete! {len(order_rows)} orders and {len(item_rows)} order line items created.")
    return True


def fetch_raw_data():
    """
    Fetches orders joined with order_items and products.
    Returns list of dicts with all normalized transaction-level columns.
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT 
        o.order_id,
        o.order_date,
        o.order_status,
        o.region,
        i.item_id,
        i.product_id,
        p.product_name,
        p.category,
        i.quantity,
        i.unit_price,
        i.discount_optional,
        i.return_amount_optional
    FROM orders o
    JOIN order_items i ON o.order_id = i.order_id
    JOIN products p ON i.product_id = p.product_id
    ORDER BY o.order_date ASC
    """

    cursor.execute(query)
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    conn.close()

    data = [dict(zip(columns, row)) for row in rows]
    return data


def test_mysql_connection(host, port, user, password, database):
    """Validates connection to external MySQL database."""
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=3
        )
        conn.close()
        return True, "Successfully connected to MySQL database!"
    except Exception as e:
        return False, str(e)


def migrate_sqlite_to_mysql(host, port, user, password, database):
    """Copies current SQLite tables and data into MySQL."""
    try:
        import mysql.connector
        # Connect to MySQL
        m_conn = mysql.connector.connect(
            host=host, port=port, user=user, password=password, database=database
        )
        m_cur = m_conn.cursor()

        # Create tables in MySQL
        m_cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) NOT NULL UNIQUE,
            username VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'Executive',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """)
        m_cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INT PRIMARY KEY,
            product_name VARCHAR(255) NOT NULL,
            category VARCHAR(100) NOT NULL
        ) ENGINE=InnoDB;
        """)
        m_cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INT PRIMARY KEY,
            order_date DATE NOT NULL,
            order_status VARCHAR(50) NOT NULL,
            region VARCHAR(100) NOT NULL
        ) ENGINE=InnoDB;
        """)
        m_cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            item_id INT PRIMARY KEY,
            order_id INT NOT NULL,
            product_id INT NOT NULL,
            quantity INT NOT NULL,
            unit_price DECIMAL(10, 2) NOT NULL,
            discount_optional DECIMAL(10, 2) DEFAULT 0.00,
            return_amount_optional DECIMAL(10, 2) DEFAULT 0.00
        ) ENGINE=InnoDB;
        """)

        # Fetch from SQLite
        s_conn = sqlite3.connect(SQLITE_DB_PATH)
        s_cur = s_conn.cursor()

        # Transfer Users
        s_cur.execute("SELECT user_id, name, email, username, password_hash, role, created_at FROM users")
        users = s_cur.fetchall()
        m_cur.execute("DELETE FROM users")
        m_cur.executemany("INSERT INTO users (user_id, name, email, username, password_hash, role, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)", users)

        # Transfer Products
        s_cur.execute("SELECT product_id, product_name, category FROM products")
        products = s_cur.fetchall()
        m_cur.execute("DELETE FROM products")
        m_cur.executemany("INSERT INTO products (product_id, product_name, category) VALUES (%s, %s, %s)", products)

        # Transfer Orders
        s_cur.execute("SELECT order_id, order_date, order_status, region FROM orders")
        orders = s_cur.fetchall()
        m_cur.execute("DELETE FROM orders")
        m_cur.executemany("INSERT INTO orders (order_id, order_date, order_status, region) VALUES (%s, %s, %s, %s)", orders)

        # Transfer Order Items
        s_cur.execute("SELECT item_id, order_id, product_id, quantity, unit_price, discount_optional, return_amount_optional FROM order_items")
        items = s_cur.fetchall()
        m_cur.execute("DELETE FROM order_items")
        m_cur.executemany("INSERT INTO order_items (item_id, order_id, product_id, quantity, unit_price, discount_optional, return_amount_optional) VALUES (%s, %s, %s, %s, %s, %s, %s)", items)

        m_conn.commit()
        m_conn.close()
        s_conn.close()
        return True, f"Successfully migrated {len(products)} products, {len(orders)} orders, and {len(items)} items to MySQL!"
    except Exception as e:
        return False, str(e)
