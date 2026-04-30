import os
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), "vocal_split.db")


def add_column_if_missing(cursor, table_name, columns, name, ddl):
    if name not in columns:
        print(f"Adding {name} column to {table_name} table...")
        cursor.execute(ddl)
    else:
        print(f"{table_name}.{name} already exists.")


def migrate():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(jobs)")
        job_columns = [row[1] for row in cursor.fetchall()]
        add_column_if_missing(cursor, "jobs", job_columns, "client_id", "ALTER TABLE jobs ADD COLUMN client_id TEXT")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_jobs_client_id ON jobs (client_id)")
        cursor.execute("UPDATE jobs SET client_id = ip_address WHERE client_id IS NULL")

        cursor.execute("PRAGMA table_info(daily_usage)")
        usage_columns = [row[1] for row in cursor.fetchall()]
        add_column_if_missing(cursor, "daily_usage", usage_columns, "client_id", "ALTER TABLE daily_usage ADD COLUMN client_id TEXT")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_daily_usage_client_id ON daily_usage (client_id)")
        cursor.execute("UPDATE daily_usage SET client_id = ip_address WHERE client_id IS NULL")

        conn.commit()
        print("client_id migration completed.")
    except Exception as exc:
        print(f"Error during migration: {exc}")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
