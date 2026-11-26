import sqlite3
from pathlib import Path
from flask import current_app, g

def get_db():
    if "db" not in g:
        Path(current_app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'customer' CHECK(role IN ('customer','admin')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL DEFAULT '',
        price REAL NOT NULL CHECK(price >= 0),
        category TEXT NOT NULL,
        image_url TEXT NOT NULL DEFAULT '',
        stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
        featured INTEGER NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS cart_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        quantity INTEGER NOT NULL DEFAULT 1 CHECK(quantity > 0),
        UNIQUE(user_id, product_id)
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        total REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'Placed',
        customer_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        address TEXT NOT NULL,
        city TEXT NOT NULL,
        postal_code TEXT NOT NULL,
        payment_method TEXT NOT NULL DEFAULT 'Cash on Delivery',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
        product_name TEXT NOT NULL,
        unit_price REAL NOT NULL,
        quantity INTEGER NOT NULL
    );
    """)
    db.commit()

def seed_products():
    db = get_db()
    count = db.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"]
    if count:
        return
    products = [
        ("Aura Wireless Headphones","aura-wireless-headphones","Immersive sound, comfortable fit and all-day battery life.",2499,"Electronics","https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=900",25,1),
        ("Nova Smart Watch","nova-smart-watch","A sleek everyday smartwatch with fitness tracking.",3999,"Accessories","https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=900",18,1),
        ("Velocity Sneakers","velocity-sneakers","Lightweight sneakers designed for everyday movement.",2199,"Fashion","https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=900",30,1),
        ("Instant Camera","instant-camera","Capture and keep your favourite moments.",5499,"Electronics","https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=900",12,1),
        ("Minimal Desk Lamp","minimal-desk-lamp","Warm ambient lighting for your workspace.",1599,"Home","https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=900",20,0),
        ("Everyday Backpack","everyday-backpack","A practical, clean design with room for essentials.",1899,"Accessories","https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=900",16,0),
        ("Classic Sunglasses","classic-sunglasses","Timeless frame with a modern finish.",999,"Fashion","https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=900",40,0),
        ("Ceramic Planter Set","ceramic-planter-set","Simple planters to bring a little green indoors.",799,"Home","https://images.unsplash.com/photo-1485955900006-10f4d324d411?w=900",22,0),
    ]
    db.executemany("""INSERT INTO products
        (name,slug,description,price,category,image_url,stock,featured)
        VALUES (?,?,?,?,?,?,?,?)""", products)
    db.commit()
