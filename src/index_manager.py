"""Index management for comic archives - creates and validates JSON index files."""

import json
import os
from pathlib import Path
from typing import Dict, Any
import xxhash
from xdg_base_dirs import xdg_cache_home

from . import archive_handler


def get_cache_dir() -> Path:
    """Return the XDG cache directory for comic viewer."""
    cache_dir = xdg_cache_home() / "comic_viewer"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_index_path(archive_path: Path) -> Path:
    """Generate index file path using xxhash of archive path."""
    archive_path = Path(archive_path).resolve()
    path_hash = xxhash.xxh64(str(archive_path).encode()).hexdigest()[:16]
    filename = f"{path_hash}_{archive_path.name}.json"
    return get_cache_dir() / filename


def compute_xxhash(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Compute xxhash64 of first 1MB + last 1MB for fast validation.

    For files smaller than 2MB, hash the entire file.
    """
    file_path = Path(file_path)
    file_size = file_path.stat().st_size
    hasher = xxhash.xxh64()

    with open(file_path, 'rb') as f:
        # Read first chunk (up to 1MB)
        first_chunk = f.read(chunk_size)
        hasher.update(first_chunk)

        # If file is larger than 2MB, also read last chunk
        if file_size > 2 * chunk_size:
            f.seek(-chunk_size, os.SEEK_END)
            last_chunk = f.read(chunk_size)
            hasher.update(last_chunk)

    return hasher.hexdigest()


def is_index_valid(index_data: Dict[str, Any], archive_path: Path) -> bool:
    """
    Validate index against current archive state.

    Three-tier validation:
    1. Check mtime (primary, instant)
    2. Check size (secondary, instant)
    3. Check xxhash (tertiary, fast but requires I/O)
    """
    archive_path = Path(archive_path)

    # Check if archive file exists
    if not archive_path.exists():
        return False

    # Get current archive stats
    stat = archive_path.stat()
    current_size = stat.st_size
    current_mtime = stat.st_mtime

    # Validate mtime (primary check)
    if index_data.get('archive_mtime') != current_mtime:
        return False

    # Validate size (secondary check)
    if index_data.get('archive_size') != current_size:
        return False

    # Validate xxhash (tertiary check - most reliable but slower)
    current_hash = compute_xxhash(archive_path)
    if index_data.get('archive_xxhash') != current_hash:
        return False

    # Validate version compatibility
    if index_data.get('version') != '1.0':
        return False

    return True


def create_index(archive_path: Path) -> Dict[str, Any]:
    """
    Create a new index for the archive.

    Scans the archive, extracts page metadata, and natural sorts pages.
    """
    import time
    start_time = time.time()

    archive_path = Path(archive_path).resolve()

    # Get archive stats
    stat = archive_path.stat()

    # Open archive and get page list
    with archive_handler.open_archive(archive_path) as zip_file:
        image_files = archive_handler.list_image_files(zip_file)
        sorted_files = archive_handler.natural_sort_pages(image_files)

        # Extract metadata for each page
        pages = []
        for idx, filename in enumerate(sorted_files):
            page_info = archive_handler.get_page_info(zip_file, filename)
            page_info['index'] = idx
            pages.append(page_info)

    # Build index
    index_data = {
        'version': '1.0',
        'archive_file': str(archive_path),
        'archive_size': stat.st_size,
        'archive_mtime': stat.st_mtime,
        'archive_xxhash': compute_xxhash(archive_path),
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'total_pages': len(pages),
        'pages': pages,
        'metadata': {
            'indexing_duration_ms': int((time.time() - start_time) * 1000),
            'viewer_version': '1.0.0'
        }
    }

    return index_data


def load_or_create_index(archive_path: Path) -> Dict[str, Any]:
    """
    Load existing index or create new one if invalid/missing.

    This is the main entry point for index operations.
    """
    archive_path = Path(archive_path).resolve()
    index_path = get_index_path(archive_path)

    # Try to load existing index
    if index_path.exists():
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)

            # Validate index
            if is_index_valid(index_data, archive_path):
                print(f"Using cached index: {index_path.name}")
                return index_data
            else:
                print(f"Index invalid, rebuilding...")
        except (json.JSONDecodeError, KeyError, OSError) as e:
            print(f"Corrupted index ({e}), rebuilding...")

    # Create new index
    print(f"Creating index for {archive_path.name}...")
    index_data = create_index(archive_path)

    # Save index to cache
    try:
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2)
        print(f"Index created: {index_path.name} ({index_data['metadata']['indexing_duration_ms']}ms)")
    except OSError as e:
        print(f"Warning: Could not save index to cache: {e}")
        print("Continuing without cached index...")

    return index_data
