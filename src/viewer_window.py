"""Tkinter-based viewer window for comic archives."""

import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from typing import Dict
from PIL import ImageTk

from .image_cache import ImageCache


class ViewerWindow:
    """
    Main viewer window with image display and navigation.

    Uses Tkinter for lightweight, zero-dependency GUI.
    """

    def __init__(self, archive_path: Path, index_data: Dict, image_cache: ImageCache):
        """
        Initialize viewer window.

        Args:
            archive_path: Path to the archive file
            index_data: Index data with page information
            image_cache: ImageCache instance
        """
        self.archive_path = archive_path
        self.index_data = index_data
        self.image_cache = image_cache

        self.current_page = 0
        self.viewing_mode = 'fit-width'  # 'fit-width', 'fit-height', 'actual'

        # Create window
        self.root = tk.Tk()
        self.root.title(f"Comic Viewer - {archive_path.name}")
        self.root.geometry("1200x900")

        # Create UI
        self._create_ui()

        # Bind keyboard shortcuts
        self._bind_shortcuts()

        # Show first page
        self.show_page(0)

        # Track window size for resize events
        self.last_window_size = (self.canvas.winfo_width(), self.canvas.winfo_height())
        self.root.bind('<Configure>', self._on_window_resize)

    def _create_ui(self):
        """Create UI components."""
        # Main frame
        main_frame = tk.Frame(self.root, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas for image display
        self.canvas = tk.Canvas(
            main_frame,
            bg='#2b2b2b',
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Status bar
        self.status_bar = tk.Label(
            self.root,
            text="",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg='#3c3c3c',
            fg='#ffffff',
            font=('Arial', 10)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Store reference to current PhotoImage (prevent garbage collection)
        self.current_photo = None

    def _bind_shortcuts(self):
        """Bind keyboard shortcuts."""
        # Navigation
        self.root.bind('<Right>', lambda e: self.next_page())
        self.root.bind('<space>', lambda e: self.next_page())
        self.root.bind('<Next>', lambda e: self.next_page())  # Page Down

        self.root.bind('<Left>', lambda e: self.previous_page())
        self.root.bind('<BackSpace>', lambda e: self.previous_page())
        self.root.bind('<Prior>', lambda e: self.previous_page())  # Page Up

        self.root.bind('<Home>', lambda e: self.first_page())
        self.root.bind('<End>', lambda e: self.last_page())

        # Viewing modes
        self.root.bind('f', lambda e: self.set_viewing_mode('fit-width'))
        self.root.bind('h', lambda e: self.set_viewing_mode('fit-height'))
        self.root.bind('a', lambda e: self.set_viewing_mode('actual'))

        # Quit
        self.root.bind('q', lambda e: self.quit())
        self.root.bind('<Escape>', lambda e: self.quit())

    def show_page(self, page_index: int):
        """
        Display a specific page.

        Args:
            page_index: Zero-based page index
        """
        if page_index < 0 or page_index >= self.index_data['total_pages']:
            return

        self.current_page = page_index

        try:
            # Get image from cache
            image = self.image_cache.get_page(page_index)

            # Get canvas size
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            # Use reasonable defaults if canvas not yet sized
            if canvas_width <= 1:
                canvas_width = 1200
            if canvas_height <= 1:
                canvas_height = 900

            # Scale image
            scaled_image = self.image_cache.scale_image(
                image,
                self.viewing_mode,
                (canvas_width, canvas_height)
            )

            # Convert to PhotoImage
            self.current_photo = ImageTk.PhotoImage(scaled_image)

            # Clear canvas and display image
            self.canvas.delete('all')
            self.canvas.create_image(
                canvas_width // 2,
                canvas_height // 2,
                image=self.current_photo,
                anchor=tk.CENTER
            )

            # Update status bar
            self._update_status()

            # Preload next page
            self.image_cache.preload_adjacent(page_index)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to display page {page_index + 1}: {e}")

    def _update_status(self):
        """Update status bar text."""
        page_num = self.current_page + 1
        total_pages = self.index_data['total_pages']
        mode_text = self.viewing_mode.replace('-', ' ').title()
        status = f"Page {page_num} of {total_pages}  |  Mode: {mode_text}  |  [←→ navigate, f/h/a modes, q quit]"
        self.status_bar.config(text=status)

    def next_page(self):
        """Navigate to next page."""
        if self.current_page < self.index_data['total_pages'] - 1:
            self.show_page(self.current_page + 1)

    def previous_page(self):
        """Navigate to previous page."""
        if self.current_page > 0:
            self.show_page(self.current_page - 1)

    def first_page(self):
        """Navigate to first page."""
        self.show_page(0)

    def last_page(self):
        """Navigate to last page."""
        self.show_page(self.index_data['total_pages'] - 1)

    def set_viewing_mode(self, mode: str):
        """
        Set viewing mode and refresh display.

        Args:
            mode: 'fit-width', 'fit-height', or 'actual'
        """
        if mode in ('fit-width', 'fit-height', 'actual'):
            self.viewing_mode = mode
            self.show_page(self.current_page)

    def _on_window_resize(self, event):
        """Handle window resize events."""
        # Only refresh if canvas was resized significantly
        if event.widget == self.root:
            new_size = (self.canvas.winfo_width(), self.canvas.winfo_height())

            # Check if size changed by more than 10 pixels
            if (abs(new_size[0] - self.last_window_size[0]) > 10 or
                    abs(new_size[1] - self.last_window_size[1]) > 10):
                self.last_window_size = new_size
                # Refresh current page with new size
                self.show_page(self.current_page)

    def quit(self):
        """Close the viewer."""
        self.root.quit()
        self.root.destroy()

    def run(self):
        """Start the Tkinter main loop."""
        self.root.mainloop()
