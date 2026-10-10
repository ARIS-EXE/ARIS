import os
from pathlib import Path


APP_DATA_DIR = (
    Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    / "RC_Inventory"
)

DB_PATH = APP_DATA_DIR / "rc_inventory.db"
IMAGE_DIR = APP_DATA_DIR / "product_images"
SETTINGS_PATH = APP_DATA_DIR / "backup_settings.json"
DEFAULT_BACKUP_DIR = APP_DATA_DIR / "backups"