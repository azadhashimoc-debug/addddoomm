import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
OUTPUT_DIR = os.path.join(DATA_DIR, "outputs")
DB_PATH = os.path.join(BASE_DIR, "vocal_split.db")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH.replace(os.sep, '/')}"
GOOGLE_WEB_CLIENT_ID = os.getenv(
    "GOOGLE_WEB_CLIENT_ID",
    "1055505176005-3bg8gh6lv2dfk4svk8dkm661g0vgt0mf.apps.googleusercontent.com",
)
GOOGLE_PLAY_PACKAGE_NAME = os.getenv(
    "GOOGLE_PLAY_PACKAGE_NAME",
    "com.vocalsplit.myapplication",
)
GOOGLE_PLAY_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT_FILE", "")
