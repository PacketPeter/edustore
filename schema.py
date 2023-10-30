import sqlite3

def create_schema():
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS districts (district_id INTEGER PRIMARY KEY, district_name TEXT UNIQUE, district_email TEXT UNIQUE)
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS district_logins (district_id INTEGER PRIMARY KEY, district_username TEXT UNIQUE, password TEXT)
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (district_id INTEGER, initials TEXT, isadmin BOOLEAN, PRIMARY KEY (district_id, initials))
    """)


    c.execute("""
    CREATE TABLE IF NOT EXISTS master_count (district_id INTEGER, part_name TEXT, count INTEGER, PRIMARY KEY (part_name))
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS additions (district_id INTEGER, part_name TEXT, manufacturer TEXT, purchase_order INTEGER, price REAL, count INTEGER, date DATETIME)
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS removals (district_id INTEGER, initials TEXT, part_name TEXT, count INTEGER, date DATETIME)
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS items (district_id INTEGER, barcode TEXT UNIQUE, part_name TEXT UNIQUE)
    """)


    c.execute("""
    CREATE TABLE IF NOT EXISTS contact (name TEXT, email TEXT, district TEXT, country TEXT)
    """)
    conn.commit()
    conn.close()