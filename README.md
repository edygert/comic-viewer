# Comic Viewer

A lightweight Linux application for viewing ZIP archives containing JPEG 2000 (.jp2) comic images.

## Features

- **Built-in File Browser**: Browse and select comics from any directory - no command-line required!
- **Fast Loading**: Creates JSON index files for instant random access to pages
- **Lightweight**: Zero external dependencies - uses Python's built-in `zipfile` and `tkinter`
- **Smart Caching**: LRU cache with preloading for smooth navigation
- **Multiple Viewing Modes**: Fit-to-width, fit-to-height, or actual size
- **Zoom & Pan**: Full zoom control with mouse wheel and keyboard shortcuts
- **Keyboard Navigation**: Arrow keys, space, page up/down, home/end
- **Persistent State**: Remembers your last page and browsing directory
- **Index Caching**: Stores metadata in `~/.cache/comic_viewer/` for faster subsequent opens

## Installation

### For End Users (Standalone Executable)

**Download and run - no Python required!**

1. Download the latest release: `comic-viewer-vX.X.X-linux-x64.tar.gz`
2. Extract: `tar -xzf comic-viewer-vX.X.X-linux-x64.tar.gz`
3. Install: `cd comic-viewer && ./install.sh`
4. Run: `comic-viewer /path/to/comic.zip`

See `DEPLOYMENT.md` for detailed deployment instructions.

### For Developers

#### Prerequisites

- Python 3.7+ (with tkinter)
- `uv` (Python package manager)

#### Setup

```bash
# Clone or navigate to the project directory
cd comic_viewer

# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Verify JPEG 2000 support
python -c "from PIL import features; print('JPEG 2000:', features.check('jpg_2000'))"
```

## Usage

### Quick Start

**Launch with file browser (easiest):**

```bash
python comic_viewer.py
```

This opens a graphical file browser where you can navigate to your comics directory and select a file. The browser will remember your last location for next time.

**Or launch directly with a file:**

```bash
python comic_viewer.py /path/to/comic.zip
```

### File Browser

The built-in file browser lets you:
- Navigate through directories with double-click or Enter
- Go to parent directory with the `..` entry at the top
- Filter automatically for comic files (`.cbz` or files containing `jp2`)
- See directories in cyan/bold, files in white
- Use arrow keys (↑/↓) to navigate the list
- Use Home/End to jump to first/last item
- Use Page Up/Page Down for faster scrolling
- Press Enter to select the highlighted file/directory
- Press Escape to exit (if no file is open) or cancel (if switching files)

While reading a comic, press `o` to open the file browser and switch to a different file.

### First Run

On first run with a file, the viewer will:
1. Scan the archive and extract page metadata
2. Create a JSON index file in `~/.cache/comic_viewer/`
3. Create a config file in `~/.config/comic_viewer/`
4. Display the first page (or last read page if returning)

### Subsequent Runs

On subsequent runs:
- Index is loaded from cache (instant startup)
- Last read page is automatically restored
- File browser starts in your last browsed directory
- Index is validated against archive (mtime, size, hash)
- Index is rebuilt automatically if archive was modified

## Keyboard Shortcuts

| Key(s) | Action |
|--------|--------|
| **Navigation** |
| `→` Right Arrow | Next page |
| `Space` | Next page |
| `Page Down` | Next page |
| `←` Left Arrow | Previous page |
| `Backspace` | Previous page |
| `Page Up` | Previous page |
| `Home` | First page |
| `End` | Last page |
| `g` | Go to page (opens dialog) |
| **Viewing Modes** |
| `f` | Fit to width |
| `h` | Fit to height |
| `a` | Actual size (or pan left when zoomed) |
| **Zoom** |
| `z` | Toggle zoom mode |
| `+` `=` | Zoom in (25% increments) |
| `-` `_` | Zoom out (25% increments) |
| `0` | Reset zoom to 100% (fit-width) |
| `Ctrl+MouseWheel` | Continuous zoom |
| **Pan (when zoomed)** |
| `w` | Pan up |
| `a` | Pan left |
| `s` | Pan down |
| `d` | Pan right |
| `MouseWheel` | Scroll vertically |
| `Shift+MouseWheel` | Scroll horizontally |
| **Other** |
| `o` | Open file browser |
| `?` | Show help screen |
| `q` | Quit |
| `Escape` | Quit |

## Archive Format

### Supported Archives

- **Format**: ZIP files (`.zip`, `.cbz`)
- **Images**: JPEG 2000 (`.jp2`) - primary format
- **Compatibility**: Also supports `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`

The file browser automatically filters for:
- Files with `.cbz` extension (case-insensitive)
- Files containing `jp2` in the filename (case-insensitive)

### Archive Structure

```
comic.zip
├── page_001.jp2
├── page_002.jp2
├── page_003.jp2
└── ...
```

Pages are automatically sorted using natural sorting:
- `page1.jp2` < `page2.jp2` < `page10.jp2` (not `page1`, `page10`, `page2`)
- Works with various naming conventions (`001.jp2`, `chapter1_page1.jp2`, etc.)

## Index Files

### Location

Index files are stored in: `~/.cache/comic_viewer/`

### Format

```json
{
  "version": "1.0",
  "archive_file": "/path/to/comic.zip",
  "archive_size": 45829345,
  "archive_mtime": 1707598234.567,
  "archive_xxhash": "a3f5e912bc456789",
  "total_pages": 24,
  "pages": [
    {
      "index": 0,
      "filename": "page_001.jp2",
      "archive_path": "page_001.jp2",
      "size": 245678,
      "compressed_size": 195432,
      "format": "JPEG2000",
      "width": 1920,
      "height": 2880
    }
  ]
}
```

### Benefits

- **Fast page count**: No need to open archive
- **Direct page access**: Jump to any page instantly
- **Pre-computed sorting**: Pages sorted once, cached forever
- **Smart scaling**: Image dimensions known before loading

### Cache Management

- **Index files**: `~/.cache/comic_viewer/` - can be safely deleted (will be recreated)
- **State files**: `~/.cache/comic_viewer/` - stores last read page per archive
- **Config file**: `~/.config/comic_viewer/config.json` - stores preferences and last directory
- Clear cache: `rm -rf ~/.cache/comic_viewer/`
- Clear config: `rm ~/.config/comic_viewer/config.json`
- Cache invalidation is automatic when archive is modified

## Dependencies

### Python Packages

- **Pillow** (12.1.0+): Image loading with JPEG 2000 support
- **natsort** (8.4.0+): Natural sorting for page order
- **xxhash** (3.5.0+): Fast hashing for cache validation
- **xdg-base-dirs** (6.0.2+): XDG cache directory support

### Built-in Modules

- `zipfile`: ZIP archive extraction (no external tools needed!)
- `tkinter`: GUI framework (included with Python)
- `json`: Index file serialization

## Architecture

### Components

1. **comic_viewer.py**: Main entry point with file switching loop
2. **config_manager.py**: Configuration and state persistence
3. **file_browser.py**: Graphical file browser dialog
4. **viewer_window.py**: Tkinter GUI with navigation and viewing
5. **index_manager.py**: Creates and validates JSON index files
6. **archive_handler.py**: ZIP extraction and page management
7. **image_cache.py**: LRU caching with preloading
8. **state_manager.py**: Last read page tracking per archive

### Performance Features

- **LRU Cache**: Keeps last 5 decoded images in memory (~50MB)
- **Preloading**: Next page loaded in background for instant navigation
- **Memory Extraction**: Images extracted directly to memory (no temp files)
- **Fast Hashing**: xxHash64 for quick archive validation (~10x faster than MD5)
- **XDG Cache**: Index files stored following Linux standards

## Troubleshooting

### JPEG 2000 Support Missing

If you see "Pillow does not have JPEG 2000 support enabled":

```bash
# Reinstall Pillow with OpenJPEG support
pip uninstall pillow
pip install --no-binary pillow pillow
```

### Archive Not Found

Ensure the file path is correct and the file exists:

```bash
ls -lh /path/to/comic.zip
```

### No Images Found

The archive must contain at least one image file with supported extensions:
- `.jp2` (JPEG 2000 - preferred)
- `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`

### Corrupted Index

If you suspect index corruption, delete it and restart:

```bash
rm ~/.cache/comic_viewer/*.json
python comic_viewer.py /path/to/comic.zip
```

### File Browser Not Showing Files

If the file browser appears empty:
- Check that you're in a directory with `.cbz` files or files containing `jp2` in the name
- File matching is case-insensitive: `.CBZ`, `.Cbz`, `JP2`, `Jp2` all match
- Use the `..` entry at the top to navigate to parent directories
- Subdirectories always show up and can be navigated into

### File Browser Window Not Visible

If the file browser doesn't appear when launching without arguments:
- Ensure you have a working X server (GUI environment)
- Try running with a file path directly: `python comic_viewer.py /path/to/comic.zip`
- Check for errors in the terminal output

## Development

### Project Structure

```
comic_viewer/
├── .venv/                    # uv virtual environment
├── .gitignore
├── README.md
├── CLAUDE.md                 # Development guide
├── DEPLOYMENT.md             # Deployment instructions
├── requirements.txt
├── comic_viewer.py          # Main entry point
└── src/
    ├── __init__.py
    ├── config_manager.py    # Configuration management
    ├── file_browser.py      # File browser dialog
    ├── viewer_window.py     # Tkinter GUI
    ├── index_manager.py     # Index creation/validation
    ├── archive_handler.py   # ZIP extraction
    ├── image_cache.py       # LRU caching
    └── state_manager.py     # Reading state tracking
```

### Running Tests

Currently no automated tests. Manual testing:

```bash
# Test file browser
python comic_viewer.py
# Should open file browser in last directory or current directory

# Test direct launch
python comic_viewer.py /path/to/test.zip

# Test file switching
# 1. Open a file
# 2. Press 'o' to open browser
# 3. Select different file
# 4. Should switch immediately

# Test config persistence
python comic_viewer.py  # Select a file from browser
python comic_viewer.py  # Should start in same directory

# Test index creation
ls ~/.cache/comic_viewer/

# Test state persistence
# 1. Open a file, navigate to page 10
# 2. Quit (q or Escape)
# 3. Reopen same file
# 4. Should resume at page 10

# Run component tests
python test_file_browser.py
```

## Building and Deploying

### Build Standalone Executable

Create a self-contained executable for deployment to other Linux machines:

```bash
# Build the executable
./build.sh

# Package for distribution
./package-release.sh 1.0.0
```

This creates:
- **Executable**: `dist/comic-viewer` (~26 MB)
- **Distribution package**: `comic-viewer-v1.0.0-linux-x64.tar.gz`

### Deployment

The standalone executable:
- **No Python required** on target machines
- **Self-contained**: includes all dependencies
- **Portable**: single file deployment
- **Cross-distribution**: works on any modern Linux (glibc 2.36+)

See **DEPLOYMENT.md** for complete deployment instructions, system requirements, and distribution methods.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

This is a personal project. For questions or issues, refer to the source code or CLAUDE.md.
