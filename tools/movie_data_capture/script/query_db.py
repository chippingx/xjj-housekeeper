
import sqlite3
import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from tools.movie_data_capture.storage import get_default_database_path

def run_query(sql_query):
    db_path = get_default_database_path()
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    # Use Row factory to access columns by name
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        cur.execute(sql_query)
        rows = cur.fetchall()
        
        if not rows:
            print("No results found.")
            return

        # Print header
        columns = rows[0].keys()
        print(" | ".join(columns))
        print("-" * (len(columns) * 10))
        
        # Print rows
        for row in rows:
            print(" | ".join(str(item) for item in row))
            
    except sqlite3.Error as e:
        print(f"SQL Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/query_db.py \"SELECT * FROM table ...\"")
    else:
        query = sys.argv[1]
        run_query(query)
