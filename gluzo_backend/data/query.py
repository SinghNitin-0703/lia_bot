import sqlite3
conn = sqlite3.connect('D:/personal Projects/resume project/Gluzo_lia 2/gluzo_backend/data/gluzo_v2.db')
cursor = conn.cursor()

# Get all tables
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
print("Tables:", tables)

for table in tables:
    table_name = table[0]
    print(f"\\n--- Table: {table_name} ---")
    try:
        # Get schema
        schema = cursor.execute(f"PRAGMA table_info({table_name});").fetchall()
        columns = [col[1] for col in schema]
        print("Columns:", columns)
        
        # See if session_id exists in this table or phone number
        rows = cursor.execute(f"SELECT * FROM {table_name} WHERE CAST(rowid AS TEXT) LIKE '%9811811202%' OR " + " OR ".join([f"CAST({col} AS TEXT) LIKE '%9811811202%'" for col in columns])).fetchall()
        for row in rows:
            print(dict(zip(columns, row)))
    except Exception as e:
        print("Error reading table", e)
