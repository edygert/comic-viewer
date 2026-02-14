#!/usr/bin/env python
"""
Comic Viewer - Lightweight viewer for ZIP archives containing JPEG 2000 images.

Usage:
    python comic_viewer.py /path/to/comic.zip
"""

import sys
import argparse
import tkinter as tk
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src import index_manager, state_manager, config_manager
from src.image_cache import ImageCache
from src.viewer_window import ViewerWindow
from src.file_browser import FileBrowser


def check_pillow_jp2_support():
    """Check if Pillow has JPEG 2000 support."""
    try:
        from PIL import features
        if not features.check('jpg_2000'):
            print("ERROR: Pillow does not have JPEG 2000 support enabled.")
            print("This is required to read .jp2 images.")
            print("\nPlease reinstall Pillow with OpenJPEG support:")
            print("  pip uninstall pillow")
            print("  pip install --no-binary pillow pillow")
            return False
    except ImportError:
        print("ERROR: Pillow is not installed.")
        print("Please install it: pip install Pillow")
        return False
    return True


def main():
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Comic Viewer - View ZIP archives containing JPEG 2000 images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Keyboard Shortcuts:
  Navigation:
    Right/Space/Page Down    Next page
    Left/Backspace/Page Up   Previous page
    Home                     First page
    End                      Last page

  Viewing Modes:
    f                        Fit to width
    h                        Fit to height
    a                        Actual size (or pan left when zoomed)

  Zoom:
    z                        Toggle zoom mode
    +/-                      Zoom in/out (25% increments)
    0                        Reset zoom to 100% (fit-width)
    Ctrl+MouseWheel          Continuous zoom

  Pan (when zoomed):
    w/a/s/d                  Pan up/left/down/right
    MouseWheel               Scroll vertically
    Shift+MouseWheel         Scroll horizontally

  Other:
    o                        Open file browser
    g                        Go to page
    ?                        Show help screen
    q/Escape                 Quit

Index Files:
  Index files are cached in ~/.cache/comic_viewer/ to speed up
  subsequent opens of the same archive.
        """
    )
    parser.add_argument(
        'archive',
        type=Path,
        nargs='?',
        help='Path to ZIP archive containing comic images (optional - opens file browser if not provided)'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='Comic Viewer 1.0.0'
    )

    args = parser.parse_args()

    # Check Pillow JPEG 2000 support once at startup
    if not check_pillow_jp2_support():
        return 1

    # Determine initial archive path
    if args.archive:
        # Direct launch: use provided argument (highest priority)
        archive_path = args.archive.resolve()
    else:
        # No CLI argument: check last opened file, then fall back to browser
        config = config_manager.load_config()

        # Try last opened file first
        last_file = config.get('last_opened_file')
        if last_file:
            last_file_path = Path(last_file)
            if last_file_path.exists() and last_file_path.is_file():
                print(f"Resuming last opened file: {last_file_path.name}")
                archive_path = last_file_path
            else:
                print(f"Last opened file not found, opening file browser...")
                last_file = None  # Clear for browser flow

        # Fall back to file browser if no last file or file doesn't exist
        if not last_file:
            # Determine starting directory for browser
            start_dir = None
            if config.get('last_browsed_directory'):
                start_dir = Path(config['last_browsed_directory'])
                # Validate directory exists, fallback to cwd if not
                if not start_dir.exists() or not start_dir.is_dir():
                    start_dir = None

            if start_dir is None:
                start_dir = Path.cwd()

            # Show file browser (no parent needed)
            browser = FileBrowser(None, start_dir)
            selected_file = browser.show()

            if not selected_file:
                print("No file selected, exiting.")
                return 0

            archive_path = selected_file

            # Remember the directory for next time
            config_manager.update_last_browsed_directory(archive_path.parent)

    # Main viewing loop - allows switching between files
    while True:
        # Verify archive exists
        if not archive_path.exists():
            print(f"ERROR: Archive not found: {archive_path}")
            return 1

        if not archive_path.is_file():
            print(f"ERROR: Not a file: {archive_path}")
            return 1

        print(f"Opening: {archive_path.name}")
        print(f"Size: {archive_path.stat().st_size / (1024*1024):.2f} MB")

        try:
            # Load or create index
            index_data = index_manager.load_or_create_index(archive_path)
            print(f"Pages: {index_data['total_pages']}")

            # Save as last opened file (after successful validation)
            config_manager.update_last_opened_file(archive_path)

            # Initialize image cache
            image_cache = ImageCache(archive_path, index_data, max_cache_size=5)

            # Load last read page if available
            initial_page = state_manager.load_state(archive_path)
            if initial_page is None or initial_page >= index_data['total_pages']:
                initial_page = 0

            # Create and run viewer window
            viewer = ViewerWindow(archive_path, index_data, image_cache, initial_page=initial_page)
            print("Launching viewer... (press 'q' to quit, 'o' to open another file)")
            next_file = viewer.run()

            # Check if user wants to open another file
            if next_file:
                print(f"Switching to: {next_file.name}")
                archive_path = next_file
                # Continue loop to open new file
            else:
                # User quit normally, exit loop
                print("Closing viewer...")
                return 0

        except ValueError as e:
            print(f"ERROR: {e}")
            return 1
        except Exception as e:
            print(f"UNEXPECTED ERROR: {e}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == '__main__':
    sys.exit(main())
