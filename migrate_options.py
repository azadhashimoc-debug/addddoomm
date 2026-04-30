import os
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), "vocal_split.db")


def add_column_if_missing(cursor, columns, name, ddl):
    if name not in columns:
        print(f"Adding {name} column to jobs table...")
        cursor.execute(ddl)
    else:
        print(f"{name} column already exists.")


def migrate():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [row[1] for row in cursor.fetchall()]

        add_column_if_missing(cursor, columns, "output_format", "ALTER TABLE jobs ADD COLUMN output_format TEXT DEFAULT 'mp3'")
        add_column_if_missing(cursor, columns, "split_mode", "ALTER TABLE jobs ADD COLUMN split_mode TEXT DEFAULT 'ai_split'")
        add_column_if_missing(cursor, columns, "quality_preset", "ALTER TABLE jobs ADD COLUMN quality_preset TEXT DEFAULT 'high'")

        conn.commit()
        print("Migration completed.")
    except Exception as exc:
        print(f"Error during migration: {exc}")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
