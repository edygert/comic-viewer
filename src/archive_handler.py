"""Archive handling for ZIP files containing comic images."""

import os
import zipfile
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image
import natsort


# Supported image extensions (prioritize .jp2, but support others for compatibility)
IMAGE_EXTENSIONS = {'.jp2', '.jpeg', '.jpg', '.png', '.gif', '.webp', '.bmp'}


def validate_archive_path(archive_path: str) -> bool:
    """
    Prevent directory traversal in ZIP file paths.

    Ensures the path doesn't escape the extraction directory.
    """
    normalized = os.path.normpath(archive_path)
    return not normalized.startswith('..') and not os.path.isabs(normalized)


def open_archive(archive_path: Path) -> zipfile.ZipFile:
    """
    Open ZIP archive for reading.

    Returns a ZipFile object (use with context manager).
    """
    try:
        return zipfile.ZipFile(archive_path, 'r')
    except zipfile.BadZipFile as e:
        raise ValueError(f"Invalid or corrupted ZIP file: {e}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Archive not found: {archive_path}")


def list_image_files(zip_file: zipfile.ZipFile) -> List[str]:
    """
    List all image files in the ZIP archive.

    Filters by extension and validates paths for security.
    """
    image_files = []

    for file_info in zip_file.filelist:
        # Skip directories
        if file_info.is_dir():
            continue

        filename = file_info.filename
        ext = Path(filename).suffix.lower()

        # Check if it's an image file
        if ext in IMAGE_EXTENSIONS:
            # Validate path for security
            if validate_archive_path(filename):
                image_files.append(filename)
            else:
                print(f"Warning: Skipping potentially unsafe path: {filename}")

    if not image_files:
        raise ValueError("No image files found in archive")

    return image_files


def natural_sort_pages(filenames: List[str]) -> List[str]:
    """
    Sort filenames using natural sorting.

    Examples:
        page1.jp2, page2.jp2, page10.jp2 (not page1, page10, page2)
        001.jp2, 002.jp2, 010.jp2
    """
    return natsort.natsorted(filenames)


def get_page_info(zip_file: zipfile.ZipFile, page_path: str) -> Dict[str, Any]:
    """
    Extract metadata for a single page.

    Returns dict with: filename, archive_path, size, compressed_size,
    format, width, height.
    """
    try:
        file_info = zip_file.getinfo(page_path)
    except KeyError:
        raise ValueError(f"Page not found in archive: {page_path}")

    # Extract image to get dimensions and format
    try:
        image_data = zip_file.read(page_path)
        with Image.open(BytesIO(image_data)) as img:
            width, height = img.size
            img_format = img.format if img.format else 'UNKNOWN'
    except Exception as e:
        # Fallback if image can't be opened
        print(f"Warning: Could not read image metadata for {page_path}: {e}")
        width, height = 0, 0
        img_format = 'UNKNOWN'

    return {
        'filename': Path(page_path).name,
        'archive_path': page_path,
        'size': file_info.file_size,
        'compressed_size': file_info.compress_size,
        'format': img_format,
        'width': width,
        'height': height
    }


def extract_page_to_memory(zip_file: zipfile.ZipFile, page_path: str) -> bytes:
    """
    Extract a single page to memory.

    Returns raw bytes (no temp files).
    """
    try:
        return zip_file.read(page_path)
    except KeyError:
        raise ValueError(f"Page not found in archive: {page_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to extract page {page_path}: {e}")
