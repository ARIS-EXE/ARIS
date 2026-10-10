import sqlite3
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path


from app_paths import (
    DB_PATH,
    IMAGE_DIR,
    DEFAULT_BACKUP_DIR,
)

BACKUP_DIR = DEFAULT_BACKUP_DIR


def create_backup():
    """
    Создаёт резервную копию базы данных и изображений товаров.
    Возвращает путь к созданному ZIP-файлу.
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Файл базы данных не найден:\n{DB_PATH}"
        )

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Проверяем целостность базы
    connection = sqlite3.connect(DB_PATH)

    try:
        result = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()

        if not result or result[0] != "ok":
            raise RuntimeError(
                "Проверка целостности базы данных не пройдена."
            )

        # Создаём временную копию базы через SQLite Backup API
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)

            temp_db = temp_dir / "rc_inventory.db"

            backup_connection = sqlite3.connect(temp_db)

            try:
                connection.backup(backup_connection)
            finally:
                backup_connection.close()

            timestamp = datetime.now().strftime(
                "%Y-%m-%d_%H%M%S"
            )

            backup_path = (
                BACKUP_DIR
                / f"RC_Inventory_Backup_{timestamp}.zip"
            )

            temp_zip = (
                BACKUP_DIR
                / f".RC_Inventory_Backup_{timestamp}.tmp"
            )

            try:
                with zipfile.ZipFile(
                    temp_zip,
                    "w",
                    compression=zipfile.ZIP_DEFLATED
                ) as archive:

                    # База данных
                    archive.write(
                        temp_db,
                        arcname="rc_inventory.db"
                    )

                    # Изображения товаров
                    if IMAGE_DIR.exists():
                        for image_file in IMAGE_DIR.iterdir():
                            if image_file.is_file():
                                archive.write(
                                    image_file,
                                    arcname=(
                                        "product_images/"
                                        + image_file.name
                                    )
                                )

                temp_zip.replace(backup_path)

            except Exception:
                if temp_zip.exists():
                    temp_zip.unlink()

                raise

    finally:
        connection.close()

    return backup_path
def restore_backup(backup_path):
    """
    Восстанавливает базу данных и изображения из ZIP-архива.
    Перед восстановлением создаёт backup текущего состояния.
    """

    backup_path = Path(backup_path)

    if not backup_path.exists():
        raise FileNotFoundError(
            f"Файл резервной копии не найден:\n{backup_path}"
        )

    if backup_path.suffix.lower() != ".zip":
        raise ValueError(
            "Выбранный файл не является ZIP-архивом."
        )

    # Проверяем содержимое архива
    with zipfile.ZipFile(backup_path, "r") as archive:
        names = archive.namelist()

        if "rc_inventory.db" not in names:
            raise ValueError(
                "В резервной копии отсутствует база данных."
            )

        # Проверяем архив на повреждение
        bad_file = archive.testzip()

        if bad_file is not None:
            raise ValueError(
                f"Архив повреждён: {bad_file}"
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)

            archive.extractall(temp_dir)

            restored_db = temp_dir / "rc_inventory.db"

            # Проверяем восстановленную БД
            test_connection = sqlite3.connect(restored_db)

            try:
                result = test_connection.execute(
                    "PRAGMA integrity_check"
                ).fetchone()

                if not result or result[0] != "ok":
                    raise ValueError(
                        "База данных внутри резервной копии "
                        "повреждена."
                    )
            finally:
                test_connection.close()

            # Сначала сохраняем текущее состояние
            create_backup()

            # Заменяем текущую базу
            shutil.copy2(
                restored_db,
                DB_PATH
            )

            # Восстанавливаем изображения
            restored_images = temp_dir / "product_images"

            if restored_images.exists():
                IMAGE_DIR.mkdir(
                    parents=True,
                    exist_ok=True
                )

                # Удаляем текущие изображения
                for image_file in IMAGE_DIR.iterdir():
                    if image_file.is_file():
                        image_file.unlink()

                # Копируем изображения из backup
                for image_file in restored_images.iterdir():
                    if image_file.is_file():
                        shutil.copy2(
                            image_file,
                            IMAGE_DIR / image_file.name
                        )

            else:
                # Если в backup изображений нет,
                # очищаем текущую папку изображений.
                if IMAGE_DIR.exists():
                    for image_file in IMAGE_DIR.iterdir():
                        if image_file.is_file():
                            image_file.unlink()

    return backup_path

def cleanup_old_backups():
    """
    Оставляет только указанное количество последних backup-файлов.
    """

    from backup.backup_settings import load_settings

    settings = load_settings()

    backup_folder = Path(
        settings["backup_folder"]
    )

    retention_count = settings[
        "retention_count"
    ]

    if not backup_folder.exists():
        return

    backups = sorted(
        backup_folder.glob(
            "RC_Inventory_Backup_*.zip"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    for old_backup in backups[retention_count:]:
        try:
            old_backup.unlink()
        except OSError:
            pass


def create_automatic_backup():
    """
    Создаёт автоматический backup не чаще одного раза в день.
    """

    from backup.backup_settings import load_settings

    settings = load_settings()

    if not settings["enabled"]:
        return None

    backup_folder = Path(
        settings["backup_folder"]
    )

    backup_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    today = datetime.now().date()

    backups = list(
        backup_folder.glob(
            "RC_Inventory_Backup_*.zip"
        )
    )

    for backup in backups:
        backup_date = datetime.fromtimestamp(
            backup.stat().st_mtime
        ).date()

        if backup_date == today:
            cleanup_old_backups()
            return None

    # Временно меняем папку назначения
    global BACKUP_DIR

    old_backup_dir = BACKUP_DIR
    BACKUP_DIR = backup_folder

    try:
        backup_path = create_backup()
    finally:
        BACKUP_DIR = old_backup_dir

    cleanup_old_backups()

    return backup_path