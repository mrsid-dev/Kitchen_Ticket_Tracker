import sqlite3, os, shutil, pytz
from kivy.utils import platform
from datetime import datetime

if platform == "android":
    from jnius import autoclass
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    app_context = PythonActivity.mActivity.getApplicationContext()
    
    # ✅ Store database directly in /files/ instead of /files/data/
    db_folder = app_context.getExternalFilesDir(None).getAbsolutePath()
else:
    db_folder = "./"  # Fallback for PC/Mac testing

db_path = os.path.join(db_folder, "kitchen_tracker.db")

def move_database_if_needed():
    """Move the database from internal storage to external storage if needed."""
    # ✅ Ensure the folder exists before moving
    if not os.path.exists(db_folder):
        print(f"Creating database folder at: {db_folder}")  # ✅ Debugging
        os.makedirs(db_folder, exist_ok=True)


    # ✅ Move the database only if it exists internally but not in external storage
    if os.path.exists("kitchen_tracker.db") and not os.path.exists(db_path):
        shutil.move("kitchen_tracker.db", db_path)
        print("Database moved to external storage.")

def init_database():
    """Create or connect to the SQLite database in external storage."""
    move_database_if_needed()  # ✅ Ensure the database is in the correct location

    # ✅ Ensure the folder exists before creating the database
    if not os.path.exists(db_folder):
        os.makedirs(db_folder, exist_ok=True)

    # ✅ Connect to the SQLite database file in the new location
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ✅ Disable WAL mode to prevent locks
    cursor.execute("PRAGMA journal_mode=DELETE;")

    # ✅ Create tables if they don't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cooks (
            pin INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clock_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            clock_in_time TEXT NOT NULL,
            clock_out_time TEXT,
            status TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cook_pin INTEGER NOT NULL,
            date TEXT NOT NULL,
            time_taken INTEGER NOT NULL,
            FOREIGN KEY (cook_pin) REFERENCES cooks (pin)
        )
    ''')

    # ✅ Commit and close connection
    conn.commit()
    conn.close()

