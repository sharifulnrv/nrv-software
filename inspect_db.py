import sqlite3

def list_tables():
    try:
        conn = sqlite3.connect('instance/nexus.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        with open('db_schema.txt', 'w') as f:
            for table in tables:
                table_name = table[0]
                f.write(f"Table: {table_name}\n")
                cursor.execute(f'PRAGMA table_info("{table_name}")')
                columns = cursor.fetchall()
                for col in columns:
                    f.write(f"  Column: {col[1]} ({col[2]})\n")
                f.write("\n")
        print("Schema written to db_schema.txt")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_tables()
