# Comic Viewer

A lightweight Linux application for viewing ZIP archives containing JPEG 2000 (.jp2) comic images.

## Features

- **Fast Loading**: Creates JSON index files for instant random access to pages
- **Lightweight**: Zero external dependencies - uses Python's built-in `zipfile` and `tkinter`
- **Smart Caching**: LRU cache with preloading for smooth navigation
- **Multiple Viewing Modes**: Fit-to-width, fit-to-height, or actual size
- **Keyboard Navigation**: Arrow keys, space, page up/down, home/end
- **Index Caching**: Stores metadata in `~/.cache/comic_viewer/` for faster subsequent opens

## Installation

### Prerequisites

- Python 3.7+ (with tkinter)
- `uv` (Python package manager)

### Setup

```bash
# Clone or navigate to the project directory
cd cbr_convert

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

### Basic Usage

```bash
python comic_viewer.py /path/to/comic.zip
```

or (if made executable):

```bash
./comic_viewer.py /path/to/comic.zip
```

### First Run

On first run, the viewer will:
1. Scan the archive and extract page metadata
2. Create a JSON index file in `~/.cache/comic_viewer/`
3. Display the first page

### Subsequent Runs

On subsequent runs:
- Index is loaded from cache (instant startup)
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
| **Viewing Modes** |
| `f` | Fit to width |
| `h` | Fit to height |
| `a` | Actual size (1:1) |
| **Application** |
| `q` | Quit |
| `Escape` | Quit |

## Archive Format

### Supported Archives

- **Format**: ZIP files (`.zip`)
- **Images**: JPEG 2000 (`.jp2`) - primary format
- **Compatibility**: Also supports `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`

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

- Index files can be safely deleted (will be recreated)
- Clear cache: `rm -rf ~/.cache/comic_viewer/`
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

1. **index_manager.py**: Creates and validates JSON index files
2. **archive_handler.py**: ZIP extraction and page management
3. **image_cache.py**: LRU caching with preloading
4. **viewer_window.py**: Tkinter GUI with navigation
5. **comic_viewer.py**: Main entry point

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

## Development

### Project Structure

```
cbr_convert/
├── .venv/                    # uv virtual environment
├── .gitignore
├── README.md
├── CLAUDE.md                 # Development guide
├── requirements.txt
├── comic_viewer.py          # Main entry point
└── src/
    ├── __init__.py
    ├── index_manager.py     # Index creation/validation
    ├── archive_handler.py   # ZIP extraction
    ├── image_cache.py       # LRU caching
    └── viewer_window.py     # Tkinter GUI
```

### Running Tests

Currently no automated tests. Manual testing:

```bash
# Test basic functionality
python comic_viewer.py /path/to/test.zip

# Test index creation
ls ~/.cache/comic_viewer/

# Test index reuse (should be faster second time)
python comic_viewer.py /path/to/test.zip
```

## License

This project is provided as-is for educational and personal use.

## Contributing

This is a personal project. For questions or issues, refer to the source code or CLAUDE.md.
