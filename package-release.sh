#!/bin/bash
# Package a release archive for distribution

set -e

VERSION=${1:-1.0.0}
ARCHIVE_NAME="comic-viewer-v${VERSION}-linux-x64.tar.gz"

echo "Packaging Comic Viewer v${VERSION} for distribution..."

# Check if executable exists
if [ ! -f "dist/comic-viewer" ]; then
    echo "ERROR: Executable not found. Please run ./build.sh first."
    exit 1
fi

# Create temporary directory for packaging
TEMP_DIR=$(mktemp -d)
PKG_DIR="$TEMP_DIR/comic-viewer"

mkdir -p "$PKG_DIR"

# Copy files to package
echo "Copying files..."
cp dist/comic-viewer "$PKG_DIR/"
cp README.md "$PKG_DIR/" 2>/dev/null || echo "README.md not found, skipping"
cp DEPLOYMENT.md "$PKG_DIR/"

# Create install script
cat > "$PKG_DIR/install.sh" << 'EOF'
#!/bin/bash
# Installation script for Comic Viewer

echo "Comic Viewer Installation"
echo "=========================="
echo ""

# Check if running as root for system-wide install
if [ "$EUID" -eq 0 ]; then
    INSTALL_PATH="/usr/local/bin/comic-viewer"
    echo "Installing system-wide to: $INSTALL_PATH"
else
    INSTALL_PATH="$HOME/.local/bin/comic-viewer"
    echo "Installing to user directory: $INSTALL_PATH"
    mkdir -p "$HOME/.local/bin"
fi

# Copy executable
cp comic-viewer "$INSTALL_PATH"
chmod +x "$INSTALL_PATH"

echo "Installation complete!"
echo ""
echo "Run with: comic-viewer /path/to/comic.zip"

if [ "$EUID" -ne 0 ]; then
    echo ""
    echo "Note: Make sure $HOME/.local/bin is in your PATH"
    echo "Add this to your ~/.bashrc or ~/.zshrc:"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
fi
EOF

chmod +x "$PKG_DIR/install.sh"

# Create README for package
cat > "$PKG_DIR/INSTALL.txt" << EOF
Comic Viewer - Installation Instructions
=========================================

Quick Start:
-----------
1. Run the install script:
   ./install.sh

2. Use the viewer:
   comic-viewer /path/to/comic.zip

Manual Installation:
-------------------
System-wide (requires sudo):
  sudo cp comic-viewer /usr/local/bin/

User-only:
  cp comic-viewer ~/.local/bin/
  (ensure ~/.local/bin is in your PATH)

Requirements:
------------
- Linux 64-bit (x86_64)
- X11 display
- glibc 2.36 or later

No Python installation required!

For detailed deployment information, see DEPLOYMENT.md

Usage:
------
  comic-viewer [options] <archive.zip>

Keyboard shortcuts:
  Right/Space     Next page
  Left/Backspace  Previous page
  f               Fit to width
  h               Fit to height
  g               Go to page
  ?               Show help
  q               Quit

For full documentation, run:
  comic-viewer --help
EOF

# Create the archive
cd "$TEMP_DIR"
tar -czf "$ARCHIVE_NAME" comic-viewer/
cd - > /dev/null

# Move to current directory
mv "$TEMP_DIR/$ARCHIVE_NAME" .

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo "Package created: $ARCHIVE_NAME"
echo "Size: $(du -h "$ARCHIVE_NAME" | cut -f1)"
echo ""
echo "To distribute:"
echo "  1. Upload $ARCHIVE_NAME to your server/repository"
echo "  2. Users download and extract: tar -xzf $ARCHIVE_NAME"
echo "  3. Users run: cd comic-viewer && ./install.sh"
echo ""
