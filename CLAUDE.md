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

1. **Archive Handler**
   - Extract images from CBR (RAR) files
   - Support CBZ (ZIP) for broader compatibility
   - Handle common image formats: JPEG, PNG, GIF, WebP
   - Natural sort ordering for page sequence

2. **Lightweight Image Display**
   - Minimal GUI framework (consider: tkinter for zero extra deps, or PyQt6/PySide6)
   - Basic navigation: next/previous page, keyboard shortcuts
   - Essential viewing modes: fit-to-width, fit-to-height, actual size
   - Fast image loading and caching

3. **File Management**
   - Temporary extraction handling
   - Cleanup on exit
   - Lazy loading for large archives

## Technical Decisions

- **Archive Extraction**: Use `rarfile` library (wraps unrar command-line tool)
- **Image Handling**: Pillow (PIL) for image loading and basic manipulation
- **GUI Framework**: Prioritize lightweight options that don't require heavy dependencies
- **No Database**: Simple file-based approach, no library management complexity

## Code Organization

Keep it simple:
- Single main script or minimal module structure
- Archive handling utilities
- Image viewer window class
- Clean separation between archive I/O and display logic
