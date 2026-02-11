"""Tkinter-based viewer window for comic archives."""

import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from typing import Dict
from PIL import Image, ImageTk

from .image_cache import ImageCache
from . import state_manager


class ViewerWindow:
    """
    Main viewer window with image display and navigation.

    Uses Tkinter for lightweight, zero-dependency GUI.
    """

    def __init__(self, archive_path: Path, index_data: Dict, image_cache: ImageCache, initial_page: int = 0):
        """
        Initialize viewer window.

        Args:
            archive_path: Path to the archive file
            index_data: Index data with page information
            image_cache: ImageCache instance
            initial_page: Initial page to display (default 0)
        """
        self.archive_path = archive_path
        self.index_data = index_data
        self.image_cache = image_cache

        self.current_page = 0
        self.viewing_mode = 'fit-width'  # 'fit-width', 'fit-height', 'actual'

        # Zoom state
        self.zoom_mode = False
        self.zoom_level = 1.0  # 1.0 = 100%, 2.0 = 200%
        self.min_zoom = 0.25
        self.max_zoom = 8.0

        # Create window
        self.root = tk.Tk()
        self.root.title(f"Comic Viewer - {archive_path.name}")
        self.root.geometry("1200x900")

        # Create UI
        self._create_ui()

        # Bind keyboard shortcuts
        self._bind_shortcuts()

        # Show initial page
        self.show_page(initial_page)

        # Track window size for resize events
        self.last_window_size = (self.canvas.winfo_width(), self.canvas.winfo_height())
        self.root.bind('<Configure>', self._on_window_resize)

    def _create_ui(self):
        """Create UI components."""
        # Main frame
        self.main_frame = tk.Frame(self.root, bg='#2b2b2b')
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas for image display (create first)
        self.canvas = tk.Canvas(
            self.main_frame,
            bg='#2b2b2b',
            highlightthickness=0
        )

        # Scrollbars (create after canvas so we can reference it)
        self.v_scrollbar = tk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.h_scrollbar = tk.Scrollbar(self.main_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)

        # Configure canvas to use scrollbars
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        # Pack canvas (scrollbars will be packed/unpacked dynamically)
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
        self.root.bind('g', lambda e: self.goto_page_dialog())

        # Viewing modes
        self.root.bind('f', lambda e: self.set_viewing_mode('fit-width'))
        self.root.bind('h', lambda e: self.set_viewing_mode('fit-height'))

        # Zoom controls
        self.root.bind('z', lambda e: self.toggle_zoom_mode())
        self.root.bind('<plus>', lambda e: self.zoom_in())
        self.root.bind('<equal>', lambda e: self.zoom_in())  # = key (+ without shift)
        self.root.bind('<KP_Add>', lambda e: self.zoom_in())  # Numpad +
        self.root.bind('<minus>', lambda e: self.zoom_out())
        self.root.bind('<underscore>', lambda e: self.zoom_out())  # _ (- with shift)
        self.root.bind('<KP_Subtract>', lambda e: self.zoom_out())  # Numpad -
        self.root.bind('0', lambda e: self.reset_zoom())

        # Mouse wheel zoom (Ctrl+Wheel)
        self.canvas.bind('<Control-MouseWheel>', self._on_ctrl_wheel)
        self.canvas.bind('<Control-Button-4>', self._on_ctrl_wheel)  # Linux scroll up
        self.canvas.bind('<Control-Button-5>', self._on_ctrl_wheel)  # Linux scroll down

        # Pan controls (WASD) and mode switching
        # These handle both pan (in zoom mode) and mode switching (not in zoom mode)
        self.root.bind('w', lambda e: self.pan_up())
        self.root.bind('s', lambda e: self.pan_down())
        self.root.bind('a', lambda e: self._handle_a_key())
        self.root.bind('d', lambda e: self.pan_right())

        # Mouse wheel scrolling (when zoomed)
        self.root.bind('<Button-4>', self._on_mouse_wheel)  # Linux scroll up
        self.root.bind('<Button-5>', self._on_mouse_wheel)  # Linux scroll down
        self.canvas.bind('<Button-4>', self._on_mouse_wheel)  # Also bind to canvas
        self.canvas.bind('<Button-5>', self._on_mouse_wheel)
        self.canvas.bind('<MouseWheel>', self._on_mouse_wheel)  # Windows/Mac
        self.root.bind('<Shift-Button-4>', self._on_shift_wheel)  # Linux horizontal
        self.root.bind('<Shift-Button-5>', self._on_shift_wheel)  # Linux horizontal
        self.canvas.bind('<Shift-Button-4>', self._on_shift_wheel)  # Also bind to canvas
        self.canvas.bind('<Shift-Button-5>', self._on_shift_wheel)

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

        # Save state (opportunistic, silent failures)
        try:
            state_manager.save_state(self.archive_path, self.current_page)
        except Exception:
            pass  # Don't disrupt viewing

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

            # Scale image based on mode
            if self.zoom_mode:
                # Apply zoom scaling
                scaled_image = self._apply_zoom(image, self.zoom_level)
            else:
                # Use existing viewing mode logic
                scaled_image = self.image_cache.scale_image(
                    image,
                    self.viewing_mode,
                    (canvas_width, canvas_height)
                )

            # Convert to PhotoImage
            self.current_photo = ImageTk.PhotoImage(scaled_image)

            # Clear canvas and display image
            self.canvas.delete('all')

            # Determine if scrolling is needed (size-based, works in any mode)
            img_width, img_height = scaled_image.size
            needs_scroll = (img_width > canvas_width or img_height > canvas_height)

            if needs_scroll:
                # Scrollable layout - use NW anchor for scrollable positioning
                self.canvas.create_image(0, 0, image=self.current_photo, anchor=tk.NW)
                self.canvas.configure(scrollregion=(0, 0, img_width, img_height))
                self._update_scrollbars(img_width, img_height)
            else:
                # Centered layout - image fits entirely in canvas
                self.canvas.create_image(
                    canvas_width // 2,
                    canvas_height // 2,
                    image=self.current_photo,
                    anchor=tk.CENTER
                )
                self.canvas.configure(scrollregion=(0, 0, 0, 0))
                self._hide_scrollbars()

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

        if self.zoom_mode:
            zoom_pct = int(self.zoom_level * 100)
            mode_text = f"Zoom {zoom_pct}%"
            shortcuts = "[←→ pages, g goto, wasd pan, +/- zoom, z exit, q quit]"
        else:
            mode_text = self.viewing_mode.replace('-', ' ').title()
            shortcuts = "[←→ navigate, g goto, f/h/a modes, z zoom, q quit]"

        status = f"Page {page_num} of {total_pages}  |  Mode: {mode_text}  |  {shortcuts}"
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

    def goto_page_dialog(self):
        """Show dialog to jump to specific page."""
        from tkinter import simpledialog

        total_pages = self.index_data['total_pages']
        current_page = self.current_page + 1  # Convert to 1-based for display

        page_num = simpledialog.askinteger(
            "Go to Page",
            f"Enter page number (1-{total_pages}):",
            initialvalue=current_page,
            minvalue=1,
            maxvalue=total_pages,
            parent=self.root
        )

        if page_num is not None:
            self.show_page(page_num - 1)  # Convert back to 0-based

    def set_viewing_mode(self, mode: str):
        """
        Set viewing mode and refresh display.

        Args:
            mode: 'fit-width', 'fit-height', or 'actual'
        """
        if mode in ('fit-width', 'fit-height', 'actual'):
            self.viewing_mode = mode
            self.zoom_mode = False  # Exit zoom when switching modes
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

                # If in zoom mode, update scrollbar visibility
                if self.zoom_mode and self.current_photo:
                    img_width = self.current_photo.width()
                    img_height = self.current_photo.height()
                    self._update_scrollbars(img_width, img_height)

    def quit(self):
        """Close the viewer."""
        # Save final state before quitting
        try:
            state_manager.save_state(self.archive_path, self.current_page)
        except Exception as e:
            print(f"Warning: Could not save state on exit: {e}")

        self.root.quit()
        self.root.destroy()

    def run(self):
        """Start the Tkinter main loop."""
        self.root.mainloop()

    def _apply_zoom(self, image, zoom_level):
        """
        Apply zoom scaling to image.

        Zoom is relative to fit-width size to maintain consistent zoom levels
        across pages with different image sizes.

        Args:
            image: PIL Image to zoom
            zoom_level: Zoom multiplier (1.0 = 100% = fit-width, 2.0 = 200%)

        Returns:
            Zoomed PIL Image
        """
        # First scale to fit-width as the base
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1:
            canvas_width = 1200
        if canvas_height <= 1:
            canvas_height = 900

        # Get fit-width dimensions
        base_image = self.image_cache.scale_image(image, 'fit-width', (canvas_width, canvas_height))
        base_width, base_height = base_image.size

        # Apply zoom to fit-width size
        new_width = int(base_width * zoom_level)
        new_height = int(base_height * zoom_level)

        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _update_scrollbars(self, img_width, img_height):
        """
        Show/hide scrollbars based on image size vs canvas size.

        Args:
            img_width: Width of the displayed image
            img_height: Height of the displayed image
        """
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Unpack both scrollbars first
        self.v_scrollbar.pack_forget()
        self.h_scrollbar.pack_forget()

        # Repack canvas to reset layout
        self.canvas.pack_forget()

        # Show scrollbars based on need
        needs_vscroll = img_height > canvas_height
        needs_hscroll = img_width > canvas_width

        if needs_vscroll:
            self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        if needs_hscroll:
            self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Repack canvas
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _hide_scrollbars(self):
        """Hide both scrollbars."""
        self.v_scrollbar.pack_forget()
        self.h_scrollbar.pack_forget()

    def toggle_zoom_mode(self):
        """Toggle zoom mode on/off."""
        self.zoom_mode = not self.zoom_mode
        if self.zoom_mode:
            # Enter zoom mode at 100%
            self.zoom_level = 1.0
            self.viewing_mode = 'zoom'
        else:
            # Exit zoom mode, return to fit-width
            self.viewing_mode = 'fit-width'
        self.show_page(self.current_page)

    def zoom_in(self):
        """Increase zoom level by 25%."""
        if not self.zoom_mode:
            self.toggle_zoom_mode()

        self.zoom_level = min(self.zoom_level + 0.25, self.max_zoom)
        self.show_page(self.current_page)

    def zoom_out(self):
        """Decrease zoom level by 25%."""
        if not self.zoom_mode:
            self.toggle_zoom_mode()

        self.zoom_level = max(self.zoom_level - 0.25, self.min_zoom)
        self.show_page(self.current_page)

    def reset_zoom(self):
        """Reset zoom to 100% and center."""
        if not self.zoom_mode:
            self.toggle_zoom_mode()

        self.zoom_level = 1.0
        self.show_page(self.current_page)
        # Center the view
        self.canvas.xview_moveto(0.25)
        self.canvas.yview_moveto(0.25)

    def _on_ctrl_wheel(self, event):
        """Handle Ctrl+MouseWheel for continuous zoom."""
        if not self.zoom_mode:
            self.toggle_zoom_mode()

        # Detect scroll direction (cross-platform)
        if hasattr(event, 'delta'):
            delta = event.delta
        else:
            # Linux: Button-4 is scroll up, Button-5 is scroll down
            delta = 1 if event.num == 4 else -1

        # Zoom in/out by 10% per wheel notch
        if delta > 0:
            self.zoom_level = min(self.zoom_level * 1.1, self.max_zoom)
        else:
            self.zoom_level = max(self.zoom_level / 1.1, self.min_zoom)

        self.show_page(self.current_page)

    def _handle_a_key(self):
        """Handle 'a' key - actual size mode or pan left depending on zoom mode."""
        if self.zoom_mode:
            self.pan_left()
        else:
            self.set_viewing_mode('actual')

    def pan_up(self):
        """Pan view upward (WASD control)."""
        if not self.zoom_mode:
            return
        self.canvas.yview_scroll(-5, tk.UNITS)

    def pan_down(self):
        """Pan view downward (WASD control)."""
        if not self.zoom_mode:
            return
        self.canvas.yview_scroll(5, tk.UNITS)

    def pan_left(self):
        """Pan view left (WASD control)."""
        if not self.zoom_mode:
            return
        self.canvas.xview_scroll(-5, tk.UNITS)

    def pan_right(self):
        """Pan view right (WASD control)."""
        if not self.zoom_mode:
            return
        self.canvas.xview_scroll(5, tk.UNITS)

    def _on_mouse_wheel(self, event):
        """Handle mouse wheel for vertical scrolling when zoomed."""
        # Check if scrolling is active (based on scrollregion, not zoom mode)
        scrollregion = self.canvas.cget('scrollregion')
        # scrollregion is empty string '' when not set, or '0 0 0 0' when disabled
        if not scrollregion or scrollregion == '' or scrollregion == '0 0 0 0':
            return "break"  # No scrolling active

        # Detect scroll direction (cross-platform)
        if hasattr(event, 'delta') and event.delta != 0:
            # Windows/Mac: delta is +/- 120
            delta = event.delta
            scroll_amount = 1 if delta > 0 else -1
        else:
            # Linux touchpad: Button-4 is scroll up, Button-5 is scroll down
            # Traditional scrolling (not inverted)
            scroll_amount = -1 if event.num == 4 else 1

        self.canvas.yview_scroll(scroll_amount, tk.UNITS)
        return "break"  # Prevent event propagation

    def _on_shift_wheel(self, event):
        """Handle Shift+MouseWheel for horizontal scrolling when zoomed."""
        # Check if scrolling is active (based on scrollregion, not zoom mode)
        scrollregion = self.canvas.cget('scrollregion')
        # scrollregion is empty string '' when not set, or '0 0 0 0' when disabled
        if not scrollregion or scrollregion == '' or scrollregion == '0 0 0 0':
            return "break"  # No scrolling active

        # Detect scroll direction (cross-platform)
        if hasattr(event, 'delta') and event.delta != 0:
            delta = event.delta
            scroll_amount = -1 if delta > 0 else 1
        else:
            # Linux touchpad: Button-4 is scroll up (left), Button-5 is scroll down (right)
            # Traditional scrolling (not inverted)
            scroll_amount = -1 if event.num == 4 else 1

        self.canvas.xview_scroll(scroll_amount, tk.UNITS)
        return "break"  # Prevent event propagation
