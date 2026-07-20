"""
Fayl (rasm) saqlash xizmati.

Hozircha lokal diskka saqlaydi (`PHOTOS_STORAGE_PATH`). Kelajakda S3/Cloud
Storage'ga o'tish uchun shu klassning ichini almashtirish yetarli - qolgan
kod (repository/service/API) o'zgarmaydi.
"""

import uuid
from pathlib import Path

from ..core.config import settings


class PhotoStorageError(Exception):
    pass


class PhotoStorageService:
    def __init__(self) -> None:
        self._base_path = Path(settings.PHOTOS_STORAGE_PATH)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def save_photo(self, content: bytes, original_filename: str, task_id: int) -> str:
        max_bytes = settings.MAX_PHOTO_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise PhotoStorageError(f"Rasm hajmi {settings.MAX_PHOTO_SIZE_MB}MB dan katta")

        suffix = Path(original_filename).suffix or ".jpg"
        filename = f"task_{task_id}_{uuid.uuid4().hex}{suffix}"

        task_dir = self._base_path / str(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)

        file_path = task_dir / filename
        file_path.write_bytes(content)

        # Nisbiy yo'lni qaytaramiz - bazada shu saqlanadi
        return str(file_path.relative_to(self._base_path))

    def get_absolute_path(self, relative_path: str) -> Path:
        return self._base_path / relative_path
