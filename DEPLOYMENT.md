# Deployment Guide - Comic Viewer

This guide covers how to build and deploy the Comic Viewer standalone executable to other Linux machines.

## Building the Executable

### Prerequisites

- Python 3.10 or later
- `uv` package manager (or pip)
- Git (optional, for cloning)

### Build Steps

1. **Set up the development environment:**

```bash
# Clone the repository (if needed)
git clone <repository-url>
cd comic_viewer

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Install PyInstaller (for building)
uv pip install pyinstaller
```

2. **Build the standalone executable:**

```bash
./build.sh
```

The build script will:
- Check for required dependencies (JPEG 2000 support)
- Clean previous builds
- Create a standalone executable using PyInstaller
- Place the executable in `dist/comic-viewer`

### Build Output

After a successful build:
- **Executable location:** `dist/comic-viewer`
- **File size:** ~26 MB
- **Format:** ELF 64-bit executable
- **Dependencies:** Fully self-contained (includes Python runtime and all libraries)

## Deploying to Other Machines

### Simple Deployment

1. **Copy the executable to the target machine:**

```bash
# Using scp
scp dist/comic-viewer user@target-machine:/tmp/

# Or using a USB drive, network share, etc.
```

2. **On the target machine, make it executable:**

```bash
chmod +x /tmp/comic-viewer
```

3. **Run the viewer:**

```bash
/tmp/comic-viewer /path/to/comic.zip
```

### System-Wide Installation

To make the viewer available system-wide:

```bash
# Copy to system bin directory
sudo cp dist/comic-viewer /usr/local/bin/

# Now you can run it from anywhere
comic-viewer /path/to/comic.zip
```

### Creating a Desktop Entry (Optional)

For integration with desktop environments, create a `.desktop` file:

```bash
sudo nano /usr/share/applications/comic-viewer.desktop
```

Add the following content:

```ini
[Desktop Entry]
Name=Comic Viewer
Comment=Lightweight comic book viewer
Exec=/usr/local/bin/comic-viewer %f
Icon=applications-graphics
Terminal=false
Type=Application
Categories=Graphics;Viewer;
MimeType=application/zip;application/x-cbz;
```

## Target Machine Requirements

### Minimal Requirements

The standalone executable has very minimal requirements on the target machine:

- **OS:** Linux (64-bit)
- **System libraries:**
  - glibc 2.36 or later
  - X11 libraries (for GUI)
  - Standard C library
- **No Python installation required**
- **No additional packages needed**

### Compatibility

The executable is built for:
- **Architecture:** x86_64 (64-bit Intel/AMD)
- **OS:** Linux with glibc 2.36+
- **Desktop:** Works with any X11-based desktop environment (GNOME, KDE, XFCE, etc.)

### Verifying System Libraries

On the target machine, check required libraries:

```bash
ldd /path/to/comic-viewer
```

All dependencies should be found. If any are missing, install the basic development libraries:

```bash
# Debian/Ubuntu
sudo apt-get install libc6 libx11-6 libxext6 libxrender1 libxft2

# Fedora/RHEL
sudo dnf install glibc libX11 libXext libXrender libXft

# Arch
sudo pacman -S glibc libx11 libxext libxrender libxft
```

## Distribution Methods

### Option 1: Direct File Transfer

- **Best for:** Single machine or small deployments
- **Method:** SCP, USB drive, shared folder
- **File:** Just copy `dist/comic-viewer`

### Option 2: Git Repository

- **Best for:** Version control and updates
- **Method:**
  1. Commit the built executable to a `releases` branch
  2. Users clone and copy the binary
  3. Update by pulling new releases

### Option 3: Web Download

- **Best for:** Public distribution
- **Method:**
  1. Upload `dist/comic-viewer` to a web server or file hosting
  2. Users download via wget/curl
  3. Example:
     ```bash
     wget https://your-server.com/comic-viewer
     chmod +x comic-viewer
     ```

### Option 4: Package Archive

- **Best for:** Bundled distribution with docs
- **Method:** Create a tarball with executable and documentation

```bash
# Create distribution package
tar -czf comic-viewer-v1.1.0-linux-x64.tar.gz \
    dist/comic-viewer \
    README.md \
    DEPLOYMENT.md

# Users extract and install
tar -xzf comic-viewer-v1.1.0-linux-x64.tar.gz
sudo cp comic-viewer /usr/local/bin/
```

## Troubleshooting

### "No such file or directory" error

- Ensure the executable has execute permissions: `chmod +x comic-viewer`
- Check if running on a 64-bit system: `uname -m` (should show x86_64)

### Missing library errors

Install basic X11 development libraries (see "Verifying System Libraries" above)

### JPEG 2000 support issues

The executable includes JPEG 2000 support. If images don't load:
- Check that the image files are valid JPEG 2000 (.jp2)
- Verify file permissions

### Performance issues

The standalone executable may have slightly slower startup than running from source, but runtime performance should be identical.

## Updating

To update the viewer on deployed machines:

1. Build a new version
2. Replace the old executable with the new one
3. User data (cache, state) is preserved in `~/.cache/comic_viewer/`

## Uninstalling

```bash
# Remove executable
sudo rm /usr/local/bin/comic-viewer

# Remove desktop entry (if created)
sudo rm /usr/share/applications/comic-viewer.desktop

# Remove user data (optional)
rm -rf ~/.cache/comic_viewer/
rm -rf ~/.local/state/comic_viewer/
```

## Build Customization

### Reducing Executable Size

Edit `comic_viewer.spec` and disable UPX compression:

```python
upx=False,  # Change to False
```

Or exclude more unnecessary modules in the `excludes` list.

### Debug Build

For troubleshooting, create a debug build:

```python
debug=True,  # Enable debug mode
console=True,  # Keep console window
```

### One-Folder Build

For easier debugging, use one-folder mode (edit the spec file):

Replace `EXE(...)` with a one-folder configuration. See PyInstaller documentation.

## Security Considerations

- The executable is fully self-contained and portable
- No network access required
- Only reads user-specified files
- Cache and state stored in standard user directories
- No elevation/root privileges needed for normal operation

## Support

For build issues or deployment problems, check:
- Build warnings: `build/comic_viewer/warn-comic_viewer.txt`
- PyInstaller logs in the build output
- System library compatibility with `ldd`
