# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A lightweight Linux application for reading and displaying CBR (Comic Book Archive) files. CBR files are RAR archives containing sequential comic book page images.

## Development Setup

- **Python Environment**: Use `uv` for virtual environment and dependency management
- **Philosophy**: Keep the viewer lightweight - minimal dependencies, fast startup, low resource usage
- **Versions**: Always use the latest stable versions of libraries, tools, and packages

### Common Commands

```bash
# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Run the application
python cbr_viewer.py [file.cbr]
```

## Architecture

### Core Components

1. **File Browser (file_browser.py)**
   - Modal Tkinter dialog for browsing directories
   - Filters for CBZ and JP2 files (case-insensitive)
   - Directory navigation with visual distinction
   - Remembers last browsed location

2. **Configuration Management (config_manager.py)**
   - JSON config at ~/.config/comic_viewer/config.json
   - Stores last browsed directory
   - Follows XDG Base Directory standards
   - Graceful error handling (print warnings, never crash)

3. **Archive Handler (archive_handler.py)**
   - Extract images from ZIP/CBZ files (uses Python's built-in zipfile)
   - Handle common image formats: JPEG 2000, PNG, GIF, WebP
   - Natural sort ordering for page sequence
   - Memory-based extraction (no temp files)

4. **Image Display & Viewing (viewer_window.py)**
   - Tkinter GUI with dark theme
   - Multiple viewing modes: fit-to-width, fit-to-height, actual size
   - Full zoom and pan support
   - Keyboard shortcuts for all operations
   - File switching support (press 'o' to open browser while viewing)

5. **Index Management (index_manager.py)**
   - JSON index files cached at ~/.cache/comic_viewer/
   - Stores page metadata for fast random access
   - Validates via mtime, size, and xxhash
   - Instant startup on subsequent opens

6. **State Tracking (state_manager.py)**
   - Remembers last read page per archive
   - Saves state automatically while reading
   - Validates state with archive hash

7. **Image Caching (image_cache.py)**
   - LRU cache keeping last 5 images in memory
   - Background preloading for smooth navigation
   - Memory-efficient decoded image storage

## Technical Decisions

- **Archive Format**: ZIP/CBZ (uses Python's built-in `zipfile` - no external dependencies)
- **Image Handling**: Pillow (PIL) for image loading with JPEG 2000 support
- **GUI Framework**: Tkinter (zero extra dependencies, included with Python)
- **Configuration**: JSON files in XDG directories (config and cache)
- **No Database**: Simple file-based approach for maximum portability
- **File Browser**: Built-in modal dialog, no need for external file managers

## Code Organization

Clean modular structure:
- **comic_viewer.py**: Main entry point with file switching loop
- **src/config_manager.py**: Configuration persistence
- **src/file_browser.py**: File browser UI component
- **src/viewer_window.py**: Main viewing window with all interactions
- **src/index_manager.py**: Index creation and validation
- **src/archive_handler.py**: ZIP extraction utilities
- **src/image_cache.py**: Image caching with LRU and preloading
- **src/state_manager.py**: Reading progress tracking

Each module has a single, clear responsibility with graceful error handling.
