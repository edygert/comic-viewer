"""Persistent disk cache for comic page thumbnails."""

from pathlib import Path
from typing import Optional

from PIL import Image
from xdg_base_dirs import xdg_cache_home


class ThumbnailCache:
    """
    Persistent JPEG thumbnail cache stored in ~/.cache/comic_viewer/thumbnails/.

    Cache keys encode the archive hash, page index, and thumbnail dimensions,
    so entries are automatically invalidated when the archive changes or the
    thumbnail size changes.

    Pruning is done by mtime: when the entry count exceeds max_entries the
    oldest files are deleted.
    """

    def __init__(
        self,
        archive_xxhash: str,
        thumb_w: int,
        thumb_h: int,
        max_entries: int = 500,
    ) -> None:
        self._thumb_w = thumb_w
        self._thumb_h = thumb_h
        self._max_entries = max_entries
        self._cache_dir = xdg_cache_home() / 'comic_viewer' / 'thumbnails' / archive_xxhash
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _entry_path(self, page_index: int) -> Path:
        name = f"{page_index}_{self._thumb_w}x{self._thumb_h}.jpg"
        return self._cache_dir / name

    def get(self, page_index: int) -> Optional[Image.Image]:
        """
        Return the cached thumbnail for page_index, or None if not cached.
        Silently deletes corrupted entries.
        """
        path = self._entry_path(page_index)
        if not path.exists():
            return None
        try:
            img = Image.open(path)
            img.load()  # read pixels now so the file handle can be released
            return img
        except Exception:
            try:
                path.unlink()
            except OSError:
                pass
            return None

    def put(self, page_index: int, img: Image.Image) -> None:
        """
        Save a thumbnail to disk. Prunes oldest entries if over max_entries.
        Silently ignores write errors.
        """
        path = self._entry_path(page_index)
        if path.exists():
            return  # already cached
        try:
            img.save(path, 'JPEG', quality=85, optimize=True)
        except Exception:
            return
        self._prune()

    def _prune(self) -> None:
        """Delete the oldest cache files if the total count exceeds max_entries."""
        try:
            entries = list(self._cache_dir.glob('*.jpg'))
            if len(entries) <= self._max_entries:
                return
            # Sort by modification time, oldest first
            entries.sort(key=lambda p: p.stat().st_mtime)
            for path in entries[:len(entries) - self._max_entries]:
                try:
                    path.unlink()
                except OSError:
                    pass
        except Exception:
            pass
