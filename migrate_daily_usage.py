import os
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), "vocal_split.db")


def migrate():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_usage (
                id TEXT PRIMARY KEY,
                ip_address TEXT NOT NULL,
                usage_date TEXT NOT NULL,
                rewarded_credits INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_daily_usage_ip_address ON daily_usage (ip_address)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_daily_usage_usage_date ON daily_usage (usage_date)")
        conn.commit()
        print("daily_usage migration completed.")
    except Exception as exc:
        print(f"Error during migration: {exc}")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
