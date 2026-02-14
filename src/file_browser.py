"""File browser dialog for selecting comic archives."""

import tkinter as tk
from tkinter import font as tkfont
from pathlib import Path
from typing import Optional


def is_comic_file(filename: str) -> bool:
    """
    Check if filename matches comic file pattern.

    Args:
        filename: Name of file to check

    Returns:
        True if file is a CBZ archive or contains "jp2" in name
    """
    filename_lower = filename.lower()
    return filename_lower.endswith('.cbz') or 'jp2' in filename_lower


class FileBrowser:
    """
    Modal file browser dialog for selecting comic archives.

    Shows directories and comic files, allows navigation through
    directory tree, and returns selected file path.
    """

    def __init__(self, parent, initial_directory: Path):
        """
        Initialize file browser dialog.

        Args:
            parent: Parent Tk window (can be None to create standalone)
            initial_directory: Directory to start browsing in
        """
        self.parent = parent
        self.current_directory = initial_directory.resolve()
        self.selected_file = None

        # Create modal dialog
        if parent is None:
            # Create standalone window
            self.dialog = tk.Tk()
        else:
            self.dialog = tk.Toplevel(parent)
            # Make modal
            self.dialog.transient(parent)
            self.dialog.grab_set()

        self.dialog.title("Select Comic Archive")
        self.dialog.geometry("700x550")
        self.dialog.configure(bg='#2b2b2b')

        # Create UI components
        self._create_ui()

        # Bind keyboard shortcuts
        self._bind_shortcuts()

        # Populate initial file list
        self._populate_list()

        # Center window
        self._center_window()

    def _create_ui(self):
        """Create UI components."""
        # Main frame
        main_frame = tk.Frame(self.dialog, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Directory label at top
        dir_frame = tk.Frame(main_frame, bg='#2b2b2b')
        dir_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            dir_frame,
            text="Directory:",
            bg='#2b2b2b',
            fg='white',
            font=('TkDefaultFont', 10, 'bold')
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.dir_label = tk.Label(
            dir_frame,
            text=str(self.current_directory),
            bg='#2b2b2b',
            fg='#00ffff',
            font=('TkDefaultFont', 10),
            anchor='w'
        )
        self.dir_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # File list frame
        list_frame = tk.Frame(main_frame, bg='#2b2b2b')
        list_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbar
        scrollbar = tk.Scrollbar(list_frame, bg='#3c3c3c')
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Listbox for files and directories
        self.listbox = tk.Listbox(
            list_frame,
            bg='#2b2b2b',
            fg='white',
            selectbackground='#4a4a4a',
            selectforeground='white',
            font=('TkDefaultFont', 11),
            yscrollcommand=scrollbar.set,
            activestyle='none',
            highlightthickness=0,
            borderwidth=0
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

        # Store mapping of listbox index to Path
        self.item_paths = []

        # Button frame
        button_frame = tk.Frame(main_frame, bg='#2b2b2b')
        button_frame.pack(fill=tk.X, pady=(10, 0))

        tk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            bg='#3c3c3c',
            fg='white',
            activebackground='#4a4a4a',
            activeforeground='white',
            borderwidth=1,
            relief=tk.RAISED,
            padx=20,
            pady=5
        ).pack(side=tk.RIGHT)

    def _bind_shortcuts(self):
        """Bind keyboard shortcuts."""
        # Enter key - open selected item
        self.listbox.bind('<Return>', self._on_select)

        # Double-click - open selected item
        self.listbox.bind('<Double-Button-1>', self._on_select)

        # Escape key - cancel
        self.dialog.bind('<Escape>', lambda e: self._on_cancel())

    def _populate_list(self):
        """Populate listbox with directories and files."""
        # Clear current list
        self.listbox.delete(0, tk.END)
        self.item_paths.clear()

        # Update directory label
        self.dir_label.config(text=str(self.current_directory))

        # Get list of items in directory
        try:
            items = list(self.current_directory.iterdir())
        except PermissionError:
            self.listbox.insert(tk.END, "  [Permission Denied]")
            self.item_paths.append(None)
            return
        except OSError as e:
            self.listbox.insert(tk.END, f"  [Error: {e}]")
            self.item_paths.append(None)
            return

        # Separate directories and files
        directories = []
        files = []

        for item in items:
            try:
                if item.is_dir():
                    directories.append(item)
                elif item.is_file() and is_comic_file(item.name):
                    files.append(item)
            except (PermissionError, OSError):
                # Skip items we can't access
                continue

        # Sort directories and files
        directories.sort(key=lambda p: p.name.lower())
        files.sort(key=lambda p: p.name.lower())

        # Add parent directory entry if not at root
        if self.current_directory.parent != self.current_directory:
            self.listbox.insert(tk.END, "  ..")
            self.item_paths.append(self.current_directory.parent)
            # Style parent entry as directory
            self.listbox.itemconfig(0, fg='#00ffff')
            try:
                bold_font = tkfont.Font(font=self.listbox['font'])
                bold_font.config(weight='bold')
                self.listbox.itemconfig(0, font=bold_font)
            except:
                pass  # Fallback if font styling fails

        # Add directories
        for directory in directories:
            display_name = f"  {directory.name}/"
            index = self.listbox.size()
            self.listbox.insert(tk.END, display_name)
            self.item_paths.append(directory)
            # Style as directory: cyan and bold
            self.listbox.itemconfig(index, fg='#00ffff')
            try:
                bold_font = tkfont.Font(font=self.listbox['font'])
                bold_font.config(weight='bold')
                self.listbox.itemconfig(index, font=bold_font)
            except:
                pass  # Fallback if font styling fails

        # Add files
        for file in files:
            display_name = f"  {file.name}"
            index = self.listbox.size()
            self.listbox.insert(tk.END, display_name)
            self.item_paths.append(file)
            # Files stay white (default)

        # Select first item if list is not empty
        if self.listbox.size() > 0:
            self.listbox.selection_set(0)
            self.listbox.activate(0)

    def _on_select(self, event):
        """Handle Enter key or double-click on selected item."""
        selection = self.listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if index >= len(self.item_paths):
            return

        selected_path = self.item_paths[index]

        if selected_path is None:
            # Error entry, do nothing
            return

        if selected_path.is_dir():
            # Navigate into directory
            self._navigate_to(selected_path)
        else:
            # File selected - close dialog and return
            self.selected_file = selected_path
            self.dialog.destroy()

    def _navigate_to(self, directory: Path):
        """
        Navigate to directory and refresh list.

        Args:
            directory: Directory to navigate to
        """
        try:
            # Verify directory exists and is accessible
            if directory.exists() and directory.is_dir():
                self.current_directory = directory.resolve()
                self._populate_list()
            else:
                print(f"Warning: Cannot access directory: {directory}")
        except (PermissionError, OSError) as e:
            print(f"Warning: Cannot navigate to {directory}: {e}")

    def _on_cancel(self):
        """Handle cancel button or Escape key."""
        self.selected_file = None
        self.dialog.destroy()

    def _center_window(self):
        """Center dialog on screen."""
        self.dialog.update_idletasks()

        # Get window and screen dimensions
        window_width = self.dialog.winfo_width()
        window_height = self.dialog.winfo_height()
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()

        # Calculate position
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        self.dialog.geometry(f"+{x}+{y}")

    def show(self) -> Optional[Path]:
        """
        Show modal dialog and return selected file.

        Returns:
            Path to selected file, or None if cancelled
        """
        # Wait for dialog to close
        self.dialog.wait_window()

        return self.selected_file
