import sqlite3

conn = sqlite3.connect("library.db")
cursor = conn.cursor()

# Create users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT
)
""")

# Create books table
cursor.execute("""
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    title TEXT,
    author TEXT,
    category TEXT,
    available INTEGER DEFAULT 1
)
""")

# Insert default admin account
cursor.execute("""
INSERT OR IGNORE INTO users (username, password, role)
VALUES ('admin', 'admin', 'admin')
""")

conn.commit()
conn.close()

print("Database created and admin user added successfully")
