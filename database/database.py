import sqlite3
from app_paths import DB_PATH


def get_connection():
    """Создаёт подключение к базе данных."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """Создаёт таблицы, если их ещё нет."""

    connection = get_connection()

    connection.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_id INTEGER,

            FOREIGN KEY (parent_id)
                REFERENCES categories(id)
        );


        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            barcode TEXT,
            manufacturer TEXT,
            part_number TEXT,
            name TEXT NOT NULL,

            category_id INTEGER,

            description TEXT,
            manufacturer_price INTEGER,
            notes TEXT,

            default_packaging INTEGER NOT NULL DEFAULT 0,
            default_buyer_shipping INTEGER NOT NULL DEFAULT 0,

            default_commission_type TEXT NOT NULL DEFAULT 'percent',
            default_commission_value REAL NOT NULL DEFAULT 0,

            deleted INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,

            FOREIGN KEY (category_id)
                REFERENCES categories(id)
        );


        CREATE TABLE IF NOT EXISTS instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            internal_number INTEGER NOT NULL UNIQUE,
            product_id INTEGER NOT NULL,

            condition TEXT NOT NULL DEFAULT 'new',

            purchase_price INTEGER NOT NULL DEFAULT 0,
            purchase_shipping INTEGER NOT NULL DEFAULT 0,
            purchase_date TEXT NOT NULL,

            status TEXT NOT NULL DEFAULT 'in_stock',

            notes TEXT,

            deleted INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            listed_date TEXT,
            FOREIGN KEY (product_id)
                REFERENCES products(id)
        );


        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            purchase_number INTEGER NOT NULL UNIQUE,
            purchase_date TEXT NOT NULL,

            total_purchase_price INTEGER NOT NULL DEFAULT 0,
            total_shipping INTEGER NOT NULL DEFAULT 0,

            created_at TEXT NOT NULL
        );


        CREATE TABLE IF NOT EXISTS purchase_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            purchase_id INTEGER NOT NULL,
            instance_id INTEGER NOT NULL,

            allocated_purchase_price INTEGER NOT NULL,
            allocated_shipping INTEGER NOT NULL,

            FOREIGN KEY (purchase_id)
                REFERENCES purchases(id),

            FOREIGN KEY (instance_id)
                REFERENCES instances(id)
        );


        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            sale_number INTEGER NOT NULL UNIQUE,
            sale_date TEXT NOT NULL,

            total_buyer_paid INTEGER,
            comment TEXT,

            created_at TEXT NOT NULL
        );


        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            sale_id INTEGER NOT NULL,
            instance_id INTEGER NOT NULL,

            sale_price INTEGER NOT NULL,
            buyer_shipping INTEGER NOT NULL DEFAULT 0,
            packaging INTEGER NOT NULL DEFAULT 0,
            commission INTEGER NOT NULL DEFAULT 0,

            profit INTEGER NOT NULL,

            active INTEGER NOT NULL DEFAULT 1,

            FOREIGN KEY (sale_id)
                REFERENCES sales(id),

            FOREIGN KEY (instance_id)
                REFERENCES instances(id)
        );


        CREATE TABLE IF NOT EXISTS returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            instance_id INTEGER NOT NULL,
            sale_id INTEGER NOT NULL,

            return_date TEXT NOT NULL,

            FOREIGN KEY (instance_id)
                REFERENCES instances(id),

            FOREIGN KEY (sale_id)
                REFERENCES sales(id)
        );


        CREATE TABLE IF NOT EXISTS write_offs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            instance_id INTEGER NOT NULL,

            write_off_date TEXT NOT NULL,
            comment TEXT NOT NULL,

            FOREIGN KEY (instance_id)
                REFERENCES instances(id)
        );


        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            event_date TEXT NOT NULL,
            event_type TEXT NOT NULL,

            instance_id INTEGER,
            product_id INTEGER,

            purchase_id INTEGER,
            sale_id INTEGER,
            return_id INTEGER,
            write_off_id INTEGER,

            amount INTEGER,
            comment TEXT
        );


        CREATE INDEX IF NOT EXISTS idx_products_barcode
            ON products(barcode);

        CREATE INDEX IF NOT EXISTS idx_products_manufacturer
            ON products(manufacturer);

        CREATE INDEX IF NOT EXISTS idx_products_part_number
            ON products(part_number);

        CREATE INDEX IF NOT EXISTS idx_instances_product
            ON instances(product_id);

        CREATE INDEX IF NOT EXISTS idx_instances_status
            ON instances(status);

        CREATE INDEX IF NOT EXISTS idx_sales_date
            ON sales(sale_date);

        CREATE INDEX IF NOT EXISTS idx_purchases_date
            ON purchases(purchase_date);

        CREATE INDEX IF NOT EXISTS idx_events_instance
            ON events(instance_id);

        DROP INDEX IF EXISTS idx_products_barcode_unique;


        CREATE TABLE IF NOT EXISTS delivery_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            shipping_cost INTEGER NOT NULL DEFAULT 0,
            packaging_cost INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );
    """)


    try:
        connection.execute(
            "ALTER TABLE instances ADD COLUMN listed_date TEXT"
        )
    except sqlite3.OperationalError as error:
        if "duplicate column name" not in str(error):
            raise

    try:
        connection.execute(
            """
            ALTER TABLE products
            ADD COLUMN default_delivery_option_id INTEGER
            """
        )
    except sqlite3.OperationalError as error:
        if "duplicate column name" not in str(error):
            raise

    try:
        connection.execute(
            "ALTER TABLE products ADD COLUMN image_path TEXT"
        )
    except sqlite3.OperationalError as error:
        if "duplicate column name" not in str(error):
            raise
    connection.commit()
    connection.close()