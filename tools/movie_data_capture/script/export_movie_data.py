
import csv
import sys
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from tools.movie_data_capture.storage import MovieDataStorage, get_default_database_path

def export_csv(output_file: str = "movie_data_export.csv"):
    db_path = get_default_database_path()
    if not Path(db_path).exists():
        print("Database not found.")
        return

    storage = MovieDataStorage(db_path)
    cur = storage.connection.cursor()
    
    # Check if alias columns exist
    cur.execute("PRAGMA table_info(movie_actress_works)")
    columns = [row[1] for row in cur.fetchall()]
    has_aliases = "other_name1" in columns

    query = """
        SELECT video_code, actress_name, release_date
        """
    if has_aliases:
        query += ", other_name1, other_name2, other_name3"
    
    query += " FROM movie_actress_works ORDER BY release_date DESC, video_code ASC"
    
    try:
        cur.execute(query)
        rows = cur.fetchall()
        
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            header = ["Video Code", "Actress Name", "Release Date"]
            if has_aliases:
                header.extend(["Alias 1", "Alias 2", "Alias 3"])
            writer.writerow(header)
            
            for row in rows:
                # Row is tuple-like
                writer.writerow(row)
                
        print(f"Exported {len(rows)} records to {output_file}")
        
    except Exception as e:
        print(f"Export failed: {e}")
    finally:
        storage.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        export_csv(sys.argv[1])
    else:
        export_csv()
