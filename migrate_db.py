import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "vocal_split.db")

def migrate():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [row[1] for row in cursor.fetchall()]

        if "file_hash" not in columns:
            print("Adding file_hash column to jobs table...")
            cursor.execute("ALTER TABLE jobs ADD COLUMN file_hash TEXT")
            cursor.execute("CREATE INDEX ix_jobs_file_hash ON jobs (file_hash)")
            print("Successfully added file_hash column.")
        else:
            print("file_hash column already exists.")

        conn.commit()
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
