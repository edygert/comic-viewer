#!/bin/bash
# Build script for Comic Viewer standalone executable

set -e  # Exit on error

echo "==================================="
echo "Comic Viewer - Build Script"
echo "==================================="
echo ""

# Activate virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Activating virtual environment..."
    if [ ! -d ".venv" ]; then
        echo "ERROR: Virtual environment not found!"
        echo "Please run: uv venv && source .venv/bin/activate && uv pip install -r requirements.txt"
        exit 1
    fi
fi

# Use venv python directly
PYTHON=".venv/bin/python3"
PYINSTALLER=".venv/bin/pyinstaller"

if [ ! -f "$PYINSTALLER" ]; then
    echo "PyInstaller not found in venv. Installing..."
    uv pip install pyinstaller
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Check for required dependencies
echo "Checking dependencies..."
$PYTHON -c "import PIL; from PIL import features; assert features.check('jpg_2000'), 'JPEG 2000 support required'" || {
    echo "ERROR: Pillow does not have JPEG 2000 support!"
    echo "Please rebuild Pillow with OpenJPEG support:"
    echo "  pip uninstall pillow"
    echo "  pip install --no-binary pillow pillow"
    exit 1
}

# Run PyInstaller
echo ""
echo "Building standalone executable with PyInstaller..."
$PYINSTALLER comic_viewer.spec

# Check if build succeeded
if [ -f "dist/comic-viewer" ]; then
    echo ""
    echo "==================================="
    echo "Build completed successfully!"
    echo "==================================="
    echo ""
    echo "Executable location: dist/comic-viewer"

    # Show file size
    SIZE=$(du -h dist/comic-viewer | cut -f1)
    echo "File size: $SIZE"

    echo ""
    echo "To deploy to another machine:"
    echo "  1. Copy dist/comic-viewer to the target machine"
    echo "  2. Make it executable: chmod +x comic-viewer"
    echo "  3. Run it: ./comic-viewer /path/to/comic.zip"
    echo ""
    echo "Optional: Move to system path for easy access:"
    echo "  sudo cp dist/comic-viewer /usr/local/bin/"
    echo ""
else
    echo "ERROR: Build failed! Executable not found."
    exit 1
fi
