"""Thumbnail browser dialog for quick page navigation."""

import math
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional, Tuple

import tkinter as tk
from PIL import Image, ImageTk

from . import archive_handler, config_manager
from .thumbnail_cache import ThumbnailCache

# Cell layout constants — column count is computed dynamically from canvas width
THUMB_W = 240   # thumbnail width (px)
THUMB_H = 320   # thumbnail max height (px, aspect-ratio preserved)
CELL_W  = 256   # THUMB_W + 16px horizontal padding
CELL_H  = 350   # THUMB_H + 30px for page number label
GUTTER  = 8     # border padding
LRU_MAX = 15    # max PhotoImage objects kept in memory (~3.5 MB at 240x320)


class ThumbnailBrowser:
    """
    Modal thumbnail grid browser for navigating comic pages.

    Virtual scrolling: only generates thumbnails for currently visible rows.
    Background threading: thumbnail generation never blocks the UI.
    LRU eviction: keeps at most LRU_MAX PhotoImage objects in memory.
    Column count adapts dynamically to the canvas width.
    """

    def __init__(
        self,
        parent: tk.Widget,
        archive_path: Path,
        index_data: Dict,
        current_page: int,
    ) -> None:
        self.parent = parent
        self.archive_path = archive_path
        self.index_data = index_data
        self.total_pages = index_data['total_pages']
        self.current_page = current_page
        self.selected_page: Optional[int] = None

        # Column count — computed from canvas width in _initial_load / _on_canvas_configure
        self._cols = 1
        self._initialized = False  # True after _initial_load sets up the real layout
        self._lru_max = LRU_MAX    # may be raised in _initial_load to cover 2 screenfuls
        self._selected_page = current_page  # keyboard-navigated selection

        # Own zip file handle (independent of image_cache to avoid thread contention)
        self._zip_file = archive_handler.open_archive(archive_path)
        self._zip_lock = threading.Lock()

        # LRU: OrderedDict mapping page_index -> PhotoImage
        self._lru: OrderedDict = OrderedDict()
        self._loaded: set = set()    # pages with PhotoImage in LRU
        self._in_flight: set = set() # pages submitted to executor

        # Disk thumbnail cache
        cfg = config_manager.load_config()
        self._thumb_cache = ThumbnailCache(
            archive_xxhash=index_data['archive_xxhash'],
            thumb_w=THUMB_W,
            thumb_h=THUMB_H,
            max_entries=cfg['thumbnail_cache_size'],
        )

        # Thread pool for thumbnail generation
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="thumb")

        # Build dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.title(f"Thumbnails \u2014 {archive_path.name}")
        self.dialog.configure(bg='#2b2b2b')
        # Size to 3/4 of screen using parent's already-valid screen dimensions
        sw = parent.winfo_screenwidth()
        sh = parent.winfo_screenheight()
        w, h = int(sw * 0.75), int(sh * 0.75)
        self.dialog.geometry(f"{w}x{h}")
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self._create_ui()
        self._bind_shortcuts()
        self._center_window()

        # Defer initial draw until dialog is rendered (need accurate canvas size)
        self.dialog.after(50, self._initial_load)

    # ── UI construction ──────────────────────────────────────────────────────

    def _create_ui(self) -> None:
        """Create UI components."""
        main_frame = tk.Frame(self.dialog, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Info bar
        tk.Label(
            main_frame,
            text=(
                f"{self.total_pages} pages  |  "
                "click thumbnail to jump  |  Esc to cancel"
            ),
            bg='#2b2b2b',
            fg='#888888',
            font=('Arial', 9),
        ).pack(side=tk.TOP, fill=tk.X, pady=(0, 4))

        # Canvas + scrollbar
        canvas_frame = tk.Frame(main_frame, bg='#2b2b2b')
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.v_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # scrollregion is set later in _initial_load once canvas width is known
        self.canvas = tk.Canvas(
            canvas_frame,
            bg='#2b2b2b',
            highlightthickness=0,
            yscrollcommand=self._make_scroll_wrapper(),
            scrollregion=(0, 0, 1, 1),
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.v_scrollbar.config(command=self.canvas.yview)

        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.bind('<Button-4>', self._on_mouse_wheel)   # Linux scroll up
        self.canvas.bind('<Button-5>', self._on_mouse_wheel)   # Linux scroll down
        self.canvas.bind('<Button-1>', self._on_click)

    def _bind_shortcuts(self) -> None:
        """Bind keyboard shortcuts."""
        self.dialog.bind('<Escape>', lambda e: self._on_cancel())
        self.dialog.bind('<Return>', lambda e: self._confirm_selection())
        self.dialog.bind('<Left>',  lambda e: self._move_selection(-1))
        self.dialog.bind('<Right>', lambda e: self._move_selection(1))
        self.dialog.bind('<Up>',    lambda e: self._move_selection(-self._cols))
        self.dialog.bind('<Down>',  lambda e: self._move_selection(self._cols))
        self.dialog.bind('<Prior>', lambda e: self._move_selection(-self._cols * 5))
        self.dialog.bind('<Next>',  lambda e: self._move_selection(self._cols * 5))
        self.dialog.bind('<Home>',  lambda e: self._move_selection_to(0))
        self.dialog.bind('<End>',   lambda e: self._move_selection_to(self.total_pages - 1))
        self.dialog.bind('j', lambda e: self._move_selection(self._cols))
        self.dialog.bind('k', lambda e: self._move_selection(-self._cols))
        self.dialog.bind('g', lambda e: self._move_selection_to(0))
        self.dialog.bind('G', lambda e: self._move_selection_to(self.total_pages - 1))

    def _center_window(self) -> None:
        """Center dialog on screen."""
        self.dialog.update_idletasks()
        w = self.dialog.winfo_width()
        h = self.dialog.winfo_height()
        sw = self.dialog.winfo_screenwidth()
        sh = self.dialog.winfo_screenheight()
        self.dialog.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    # ── Canvas geometry helpers ───────────────────────────────────────────────

    def _compute_cols(self) -> int:
        """Compute column count from current canvas width."""
        canvas_w = self.canvas.winfo_width()
        if canvas_w <= 1:
            canvas_w = 800  # fallback before canvas is rendered
        return max(1, canvas_w // CELL_W)

    def _update_scrollregion(self) -> None:
        """Set canvas scrollregion based on current column count."""
        total_rows = math.ceil(self.total_pages / self._cols)
        total_w = self._cols * CELL_W + GUTTER
        total_h = total_rows * CELL_H + GUTTER
        self.canvas.configure(scrollregion=(0, 0, total_w, total_h))

    def _page_to_cell(self, page_index: int) -> Tuple[int, int]:
        """Return (col, row) for a zero-based page index."""
        return page_index % self._cols, page_index // self._cols

    def _cell_bbox(self, col: int, row: int) -> Tuple[int, int, int, int]:
        """Return (x0, y0, x1, y1) canvas coords for a cell."""
        x0 = GUTTER // 2 + col * CELL_W
        y0 = GUTTER // 2 + row * CELL_H
        return x0, y0, x0 + CELL_W - 2, y0 + CELL_H - 2

    # ── Scroll / resize handling ──────────────────────────────────────────────

    def _make_scroll_wrapper(self):
        """Return a yscrollcommand that also triggers visible-range check."""
        def scroll_set(first, last):
            self.v_scrollbar.set(first, last)
            self._check_visible_range()
        return scroll_set

    def _on_mouse_wheel(self, event) -> None:
        """Handle Linux mouse wheel scrolling."""
        direction = -3 if event.num == 4 else 3
        self.canvas.yview_scroll(direction, 'units')
        self._check_visible_range()

    def _on_canvas_configure(self, event) -> None:
        """Canvas resized — recompute columns and redraw if layout changed."""
        if not self._initialized:
            return
        new_cols = self._compute_cols()
        if new_cols != self._cols:
            self._cols = new_cols
            self._redraw_all()
        else:
            self._check_visible_range()

    def _check_visible_range(self) -> None:
        """Request thumbnail loading for all currently visible pages."""
        if not self._initialized or not self.dialog.winfo_exists():
            return
        total_rows = math.ceil(self.total_pages / self._cols)
        total_h = total_rows * CELL_H
        if total_h == 0:
            return

        top_frac, bot_frac = self.canvas.yview()
        first_row = max(0, int(top_frac * total_h / CELL_H) - 1)
        last_row = min(total_rows - 1, int(bot_frac * total_h / CELL_H) + 1)

        first_page = first_row * self._cols
        last_page = min(self.total_pages - 1, (last_row + 1) * self._cols - 1)

        for page_index in range(first_page, last_page + 1):
            self._request_thumbnail(page_index)

    # ── Canvas drawing ────────────────────────────────────────────────────────

    def _draw_placeholder(self, page_index: int) -> None:
        """Draw a dark-gray rect + page number for one cell."""
        col, row = self._page_to_cell(page_index)
        x0, y0, x1, y1 = self._cell_bbox(col, row)
        tag = f"cell_{page_index}"
        self.canvas.delete(tag)
        self.canvas.create_rectangle(
            x0, y0, x1, y1,
            fill='#3a3a3a', outline='#555555',
            tags=(tag, 'placeholder'),
        )
        self.canvas.create_text(
            (x0 + x1) // 2, y1 - 10,
            text=str(page_index + 1),
            fill='#777777', font=('Arial', 9),
            tags=(tag, 'pagelabel'),
        )

    def _draw_thumbnail(self, page_index: int, photo: ImageTk.PhotoImage) -> None:
        """Replace placeholder with actual thumbnail image."""
        if not self.dialog.winfo_exists():
            return
        col, row = self._page_to_cell(page_index)
        x0, y0, x1, y1 = self._cell_bbox(col, row)
        tag = f"cell_{page_index}"
        cell_inner_w = CELL_W - 2
        cell_inner_h = CELL_H - 2 - 20  # reserve 20px at bottom for label

        self.canvas.delete(tag)

        # Center thumbnail within the cell area
        img_x = x0 + (cell_inner_w - photo.width()) // 2
        img_y = y0 + (cell_inner_h - photo.height()) // 2
        self.canvas.create_image(
            img_x, img_y,
            image=photo, anchor=tk.NW,
            tags=(tag, 'thumb'),
        )
        self.canvas.create_text(
            (x0 + x1) // 2, y1 - 6,
            text=str(page_index + 1),
            fill='#cccccc', font=('Arial', 9),
            tags=(tag, 'pagelabel'),
        )
        if page_index == self.current_page:
            self._draw_highlight(page_index)

    def _draw_highlight(self, page_index: int) -> None:
        """Draw a cyan border around the current page cell."""
        col, row = self._page_to_cell(page_index)
        x0, y0, x1, y1 = self._cell_bbox(col, row)
        htag = f"highlight_{page_index}"
        self.canvas.delete(htag)
        self.canvas.create_rectangle(
            x0, y0, x1, y1,
            outline='#00aaff', width=3,
            tags=(htag, 'highlight'),
        )
        self.canvas.tag_raise(htag)

    def _draw_selection(self, page_index: int) -> None:
        """Draw a white inset border on the keyboard-selected cell."""
        col, row = self._page_to_cell(page_index)
        x0, y0, x1, y1 = self._cell_bbox(col, row)
        stag = f"selection_{page_index}"
        self.canvas.delete(stag)
        self.canvas.create_rectangle(
            x0 + 4, y0 + 4, x1 - 4, y1 - 4,
            outline='#ffffff', width=2,
            tags=(stag, 'selection'),
        )
        self.canvas.tag_raise(stag)

    def _move_selection(self, delta: int) -> None:
        """Move the keyboard selection by delta pages, clamped to valid range."""
        new_page = max(0, min(self.total_pages - 1, self._selected_page + delta))
        self._move_selection_to(new_page)

    def _move_selection_to(self, page_index: int) -> None:
        """Move keyboard selection to a specific page index."""
        old = self._selected_page
        self._selected_page = page_index
        self.canvas.delete(f"selection_{old}")
        self._draw_selection(self._selected_page)
        self._ensure_page_visible(self._selected_page)
        self._request_thumbnail(self._selected_page)

    def _is_page_strictly_visible(self, page_index: int) -> bool:
        """Return True if page_index is within the strictly visible rows (no lookahead)."""
        total_rows = math.ceil(self.total_pages / self._cols)
        total_h = total_rows * CELL_H
        if total_h == 0:
            return False
        top_frac, bot_frac = self.canvas.yview()
        first_row = int(top_frac * total_h / CELL_H)
        last_row = min(total_rows - 1, int(bot_frac * total_h / CELL_H))
        _, row = self._page_to_cell(page_index)
        return first_row <= row <= last_row

    def _ensure_page_visible(self, page_index: int) -> None:
        """Scroll if needed to bring page_index into view, then load visible range."""
        if not self._is_page_strictly_visible(page_index):
            self._scroll_to_page(page_index)
        self._check_visible_range()

    def _confirm_selection(self) -> None:
        """Navigate to the currently selected page and close."""
        self.selected_page = self._selected_page
        self._cleanup()
        self.dialog.destroy()

    # ── Initial draw and relayout ─────────────────────────────────────────────

    def _initial_load(self) -> None:
        """
        Called 50ms after dialog opens.
        Compute columns from actual canvas width, draw all placeholders,
        scroll to current page, and kick off visible thumbnail loads.
        """
        if not self.dialog.winfo_exists():
            return
        self._cols = self._compute_cols()
        self._initialized = True
        canvas_h = self.canvas.winfo_height()
        if canvas_h <= 1:
            canvas_h = 600
        visible_rows = math.ceil(canvas_h / CELL_H) + 1
        self._lru_max = max(LRU_MAX, 2 * visible_rows * self._cols)
        self._update_scrollregion()
        for i in range(self.total_pages):
            self._draw_placeholder(i)
        self._draw_highlight(self.current_page)
        self._draw_selection(self._selected_page)
        self._scroll_to_page(self.current_page)
        self._check_visible_range()

    def _redraw_all(self) -> None:
        """Redraw every cell after a column-count change."""
        self._update_scrollregion()
        self.canvas.delete('all')
        for i in range(self.total_pages):
            self._draw_placeholder(i)
        self._draw_highlight(self.current_page)
        self._draw_selection(self._selected_page)
        for page_index, photo in list(self._lru.items()):
            self._draw_thumbnail(page_index, photo)
        self._check_visible_range()

    def _scroll_to_page(self, page_index: int) -> None:
        """Scroll canvas so the given page is roughly centered."""
        total_rows = math.ceil(self.total_pages / self._cols)
        total_h = total_rows * CELL_H
        if total_h == 0:
            return
        _, row = self._page_to_cell(page_index)
        canvas_h = self.canvas.winfo_height()
        if canvas_h <= 1:
            canvas_h = 600
        target_y = max(0, row * CELL_H - canvas_h // 2 + CELL_H // 2)
        fraction = target_y / total_h
        self.canvas.yview_moveto(min(fraction, 1.0))

    def _scroll_keys(self, rows: int) -> None:
        """Scroll by a number of rows and refresh visible thumbnails."""
        self.canvas.yview_scroll(rows, 'units')
        self._check_visible_range()

    # ── Threading ─────────────────────────────────────────────────────────────

    def _request_thumbnail(self, page_index: int) -> None:
        """Submit page_index for thumbnail generation if not already done."""
        if page_index in self._loaded or page_index in self._in_flight:
            return
        self._in_flight.add(page_index)
        self._executor.submit(self._thumbnail_worker, page_index)

    def _thumbnail_worker(self, page_index: int) -> None:
        """
        Background thread: extract page, decode, resize to thumbnail.
        Posts PIL Image to main thread via after().
        """
        try:
            # Check disk cache before touching the archive
            img = self._thumb_cache.get(page_index)

            if img is None:
                page_info = self.index_data['pages'][page_index]
                archive_path = page_info['archive_path']

                with self._zip_lock:
                    image_data = archive_handler.extract_page_to_memory(
                        self._zip_file, archive_path
                    )

                img = Image.open(BytesIO(image_data))
                if img.mode == 'RGBA':
                    bg = Image.new('RGB', img.size, (42, 42, 42))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                # Preserve aspect ratio, fit within THUMB_W x THUMB_H
                img.thumbnail((THUMB_W, THUMB_H), Image.Resampling.LANCZOS)

                # Persist to disk for future sessions
                self._thumb_cache.put(page_index, img)

            # Schedule UI update on main thread
            try:
                self.canvas.after(0, self._on_thumbnail_ready, page_index, img)
            except tk.TclError:
                img.close()  # Dialog was closed
        except Exception:
            try:
                self.canvas.after(0, self._in_flight.discard, page_index)
            except tk.TclError:
                pass

    def _on_thumbnail_ready(self, page_index: int, pil_img: Image.Image) -> None:
        """Main-thread callback: convert PIL Image to PhotoImage and paint cell."""
        self._in_flight.discard(page_index)
        if not self.dialog.winfo_exists():
            pil_img.close()
            return
        photo = ImageTk.PhotoImage(pil_img)
        pil_img.close()
        self._lru_add(page_index, photo)
        self._loaded.add(page_index)
        self._draw_thumbnail(page_index, photo)

    # ── LRU management ────────────────────────────────────────────────────────

    def _lru_add(self, page_index: int, photo: ImageTk.PhotoImage) -> None:
        """Add entry to LRU, evicting oldest if over _lru_max."""
        if page_index in self._lru:
            self._lru.move_to_end(page_index)
            return
        self._lru[page_index] = photo
        while len(self._lru) > self._lru_max:
            evicted_index, _ = self._lru.popitem(last=False)
            self._loaded.discard(evicted_index)
            self._draw_placeholder(evicted_index)

    # ── Selection / navigation ────────────────────────────────────────────────

    def _on_click(self, event) -> None:
        """Map canvas click coords to page index and navigate."""
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        col = int((cx - GUTTER // 2) / CELL_W)
        row = int((cy - GUTTER // 2) / CELL_H)
        if col < 0 or col >= self._cols:
            return
        page_index = row * self._cols + col
        if 0 <= page_index < self.total_pages:
            self.selected_page = page_index
            self._cleanup()
            self.dialog.destroy()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _cleanup(self) -> None:
        """Shut down executor and close zip file."""
        try:
            self._executor.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            # cancel_futures requires Python 3.9+
            self._executor.shutdown(wait=False)
        try:
            self._zip_file.close()
        except Exception:
            pass

    def _on_cancel(self) -> None:
        """Handle Escape key or window close — cancel without navigating."""
        self.selected_page = None
        self._cleanup()
        self.dialog.destroy()

    def show(self) -> Optional[int]:
        """
        Show modal dialog.

        Returns:
            Selected page index (0-based), or None if cancelled.
        """
        self.dialog.wait_window()
        return self.selected_page
