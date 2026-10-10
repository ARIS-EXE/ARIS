import json
from app_paths import (
    SETTINGS_PATH,
    DEFAULT_BACKUP_DIR,
)

DEFAULT_SETTINGS = {
    "enabled": True,
    "retention_count": 10,
    "backup_folder": str(DEFAULT_BACKUP_DIR),
}


def load_settings():
    if not SETTINGS_PATH.exists():
        save_settings(DEFAULT_SETTINGS.copy())

    try:
        with open(
            SETTINGS_PATH,
            "r",
            encoding="utf-8"
        ) as file:
            settings = json.load(file)

    except (OSError, json.JSONDecodeError):
        settings = DEFAULT_SETTINGS.copy()
        save_settings(settings)

    return {
        "enabled": bool(
            settings.get(
                "enabled",
                DEFAULT_SETTINGS["enabled"]
            )
        ),
        "retention_count": max(
            1,
            int(
                settings.get(
                    "retention_count",
                    DEFAULT_SETTINGS["retention_count"]
                )
            )
        ),
        "backup_folder": str(
            settings.get(
                "backup_folder",
                DEFAULT_SETTINGS["backup_folder"]
            )
        ),
    }


def save_settings(settings):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(SETTINGS_PATH, "w", encoding="utf-8") as file:
        json.dump(
            settings,
            file,
            ensure_ascii=False,
            indent=4
        )