"""State management for comic viewer - tracks last read page per archive."""

import json
from pathlib import Path
from typing import Optional
import xxhash

from .index_manager import get_cache_dir, compute_xxhash


def get_state_path(archive_path: Path) -> Path:
    """
    Generate state file path using xxhash of archive path.

    Similar to index files, but uses _state.json suffix.
    """
    archive_path = Path(archive_path).resolve()
    path_hash = xxhash.xxh64(str(archive_path).encode()).hexdigest()[:16]
    filename = f"{path_hash}_state.json"
    return get_cache_dir() / filename


def is_state_valid(state_data: dict, archive_path: Path) -> bool:
    """
    Validate state file against current archive.

    Checks:
    1. Version compatibility
    2. Archive file path matches
    3. Archive xxhash matches (detects file modifications)
    """
    archive_path = Path(archive_path).resolve()

    # Check if archive file exists
    if not archive_path.exists():
        return False

    # Validate version
    if state_data.get('version') != '1.0':
        return False

    # Validate archive path
    if state_data.get('archive_file') != str(archive_path):
        return False

    # Validate xxhash (detects if archive was modified/replaced)
    try:
        current_hash = compute_xxhash(archive_path)
        if state_data.get('archive_xxhash') != current_hash:
            return False
    except Exception:
        return False

    return True


def load_state(archive_path: Path) -> Optional[int]:
    """
    Load last read page for archive.

    Returns:
        Page index (0-based) if valid state exists, None otherwise.

    Graceful error handling - all failures return None.
    """
    archive_path = Path(archive_path).resolve()
    state_path = get_state_path(archive_path)

    # Check if state file exists
    if not state_path.exists():
        return None

    # Try to load state file
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Warning: Corrupted state file, starting at page 0: {e}")
        return None
    except OSError as e:
        print(f"Warning: Could not read state file: {e}")
        return None

    # Validate state
    if not is_state_valid(state_data, archive_path):
        print("Warning: Archive modified or state invalid, starting at page 0")
        return None

    # Extract last page
    last_page = state_data.get('last_page')
    if not isinstance(last_page, int) or last_page < 0:
        print(f"Warning: Invalid page index in state: {last_page}")
        return None

    return last_page


def save_state(archive_path: Path, page_index: int) -> None:
    """
    Save current page for archive.

    Args:
        archive_path: Path to the archive file
        page_index: Current page index (0-based)

    Silent error handling - failures are logged but don't raise exceptions.
    """
    import time

    archive_path = Path(archive_path).resolve()
    state_path = get_state_path(archive_path)

    # Build state data
    try:
        state_data = {
            'version': '1.0',
            'archive_file': str(archive_path),
            'archive_xxhash': compute_xxhash(archive_path),
            'last_page': page_index,
            'updated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }
    except Exception as e:
        print(f"Warning: Could not compute state data: {e}")
        return

    # Write state file
    try:
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2)
    except OSError as e:
        print(f"Warning: Could not save state: {e}")
