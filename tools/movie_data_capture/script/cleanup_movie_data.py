
import sys
import os
import sqlite3
from pathlib import Path

# Standalone cleanup script to avoid import errors from broken dependencies

def get_default_database_path() -> str:
    # Mimic logic from tools.video_info_collector.cli
    # Default path based on observation of storage.py fallback
    default_path = "output/video_info_collector/database/video_database.db"
    
    # Check env var
    env_db = os.getenv("MOVIE_DATA_CAPTURE_DB_PATH")
    if env_db:
        return env_db
        
    # Try to resolve relative to project root if possible
    # Assuming this script is in tools/movie_data_capture/script/
    project_root = Path(__file__).resolve().parents[3]
    
    # Try to find the file if it exists in expected locations
    candidate = project_root / default_path
    if candidate.exists():
        return str(candidate)
        
    return str(candidate)

def cleanup():
    db_path = get_default_database_path()
    print(f"Using database at: {db_path}")
    
    if not os.path.exists(db_path):
        print("Database file not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # 1. Clear movie_actress_works table
        # Check if table exists first
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='movie_actress_works'")
        if cur.fetchone():
            print("Clearing 'movie_actress_works' table...")
            cur.execute("DELETE FROM movie_actress_works")
            deleted_count = cur.rowcount
            print(f"Deleted {deleted_count} rows from 'movie_actress_works'.")
        else:
            print("Table 'movie_actress_works' does not exist.")
        
        # 2. Drop movie_video_actresses table if exists
        # print("Dropping 'movie_video_actresses' table...")
        # cur.execute("DROP TABLE IF EXISTS movie_video_actresses")
        # print("Table 'movie_video_actresses' dropped (if it existed).")
        
        conn.commit()
        print("Cleanup successful.")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    cleanup()
