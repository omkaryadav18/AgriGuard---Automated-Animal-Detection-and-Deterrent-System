import sqlite3

DATABASE_FILE = 'database.db'
print(f"Setting up database: {DATABASE_FILE}")

conn = sqlite3.connect(DATABASE_FILE)
cursor = conn.cursor()

# --- Users Table ---
# This matches the table in your app.py
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
)
''')
print("Created 'users' table.")

# --- Detections Table ---
# This matches the table in your app.py
cursor.execute('''
CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    animal_name TEXT NOT NULL,
    image_path TEXT NOT NULL
)
''')
print("Created 'detections' table.")

conn.commit()
conn.close()

print("Database setup complete. You can now run 'app.py'.")