"""Image caching and loading for comic viewer."""

from io import BytesIO
from pathlib import Path
from typing import Dict, Optional, Tuple
import threading
import zipfile
from PIL import Image

from . import archive_handler


class ImageCache:
    """
    LRU cache for decoded images with preloading support.

    Keeps recently viewed pages in memory for instant navigation.
    """

    def __init__(self, archive_path: Path, index_data: Dict, max_cache_size: int = 5):
        """
        Initialize image cache.

        Args:
            archive_path: Path to the ZIP archive
            index_data: Index data with page information
            max_cache_size: Maximum number of images to keep in cache
        """
        self.archive_path = Path(archive_path)
        self.index_data = index_data
        self.max_cache_size = max_cache_size

        # LRU cache: {page_index: PIL.Image}
        self.cache: Dict[int, Image.Image] = {}
        self.access_order: list = []  # Track access order for LRU

        # Preload thread management
        self.preload_thread: Optional[threading.Thread] = None
        self.preload_cancel = threading.Event()

        # Open ZIP file (keep it open for performance)
        self.zip_file = archive_handler.open_archive(archive_path)

    def __del__(self):
        """Clean up resources."""
        self.clear_cache()
        if hasattr(self, 'zip_file'):
            self.zip_file.close()

    def get_page(self, page_index: int) -> Image.Image:
        """
        Get page image by index.

        Returns cached image if available, otherwise loads from archive.
        """
        if page_index < 0 or page_index >= self.index_data['total_pages']:
            raise ValueError(f"Invalid page index: {page_index}")

        # Check cache
        if page_index in self.cache:
            # Move to end of access order (most recently used)
            self.access_order.remove(page_index)
            self.access_order.append(page_index)
            return self.cache[page_index]

        # Load from archive
        image = self._load_page(page_index)

        # Add to cache
        self._add_to_cache(page_index, image)

        return image

    def _load_page(self, page_index: int) -> Image.Image:
        """Load page from archive."""
        page_info = self.index_data['pages'][page_index]
        archive_path = page_info['archive_path']

        # Extract to memory
        image_data = archive_handler.extract_page_to_memory(self.zip_file, archive_path)

        # Open with PIL
        image = Image.open(BytesIO(image_data))

        # Convert to RGB if necessary (for consistent handling)
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGB')

        return image

    def _add_to_cache(self, page_index: int, image: Image.Image):
        """Add image to cache with LRU eviction."""
        # Evict oldest if cache is full
        while len(self.cache) >= self.max_cache_size:
            oldest = self.access_order.pop(0)
            if oldest in self.cache:
                self.cache[oldest].close()
                del self.cache[oldest]

        # Add new image
        self.cache[page_index] = image
        self.access_order.append(page_index)

    def scale_image(self, image: Image.Image, mode: str, window_size: Tuple[int, int]) -> Image.Image:
        """
        Scale image according to viewing mode.

        Args:
            image: PIL Image to scale
            mode: 'fit-width', 'fit-height', or 'actual'
            window_size: (width, height) of display area

        Returns:
            Scaled PIL Image
        """
        if mode == 'actual':
            return image

        window_width, window_height = window_size
        img_width, img_height = image.size

        if mode == 'fit-width':
            # Scale to fit width, maintain aspect ratio
            scale = window_width / img_width
            new_width = window_width
            new_height = int(img_height * scale)
        elif mode == 'fit-height':
            # Scale to fit height, maintain aspect ratio
            scale = window_height / img_height
            new_width = int(img_width * scale)
            new_height = window_height
        else:
            # Default to fit-width
            scale = window_width / img_width
            new_width = window_width
            new_height = int(img_height * scale)

        # Only scale down or if scale factor is reasonable
        if new_width <= 0 or new_height <= 0:
            return image

        # Use high-quality resampling
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def preload_adjacent(self, current_index: int):
        """
        Preload next page in background.

        Cancels any existing preload operation.
        """
        # Cancel existing preload
        if self.preload_thread and self.preload_thread.is_alive():
            self.preload_cancel.set()
            self.preload_thread.join(timeout=0.1)

        # Reset cancel flag
        self.preload_cancel.clear()

        # Start new preload thread
        self.preload_thread = threading.Thread(
            target=self._preload_worker,
            args=(current_index,),
            daemon=True
        )
        self.preload_thread.start()

    def _preload_worker(self, current_index: int):
        """Background worker for preloading next page."""
        next_index = current_index + 1

        # Check if next page exists and is not cached
        if next_index < self.index_data['total_pages'] and next_index not in self.cache:
            if not self.preload_cancel.is_set():
                try:
                    image = self._load_page(next_index)
                    if not self.preload_cancel.is_set():
                        self._add_to_cache(next_index, image)
                except Exception as e:
                    # Silently fail on preload errors
                    print(f"Preload failed for page {next_index}: {e}")

    def clear_cache(self):
        """Clear all cached images."""
        for image in self.cache.values():
            image.close()
        self.cache.clear()
        self.access_order.clear()
