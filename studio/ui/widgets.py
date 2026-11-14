"""Shared UI pieces: colours, the Windows clipboard (text + formatted HTML) and a scrolling panel."""
import sys
import time
import tkinter as tk
from tkinter import ttk

BG, CARD, INK, MUTED, LINE = "#F4F6FA", "#FFFFFF", "#14213D", "#5B6475", "#E2E6EE"
BRAND, OK, CHIP = "#0B2A8A", "#1E8E5A", "#EEF2FB"
FONT = "Segoe UI"


# ---------------------------------------------------------------------------
# Clipboard: plain text, or HTML + text (so the description keeps its formatting)
# ---------------------------------------------------------------------------
def set_clipboard(text, html_fragment=None, tk_root=None):
    if sys.platform != "win32":
        tk_root.clipboard_clear()
        tk_root.clipboard_append(text)
        return True
    import ctypes
    from ctypes import wintypes
    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    k32.GlobalAlloc.restype = wintypes.HGLOBAL
    k32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    k32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    u32.SetClipboardData.restype = wintypes.HANDLE
    u32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    u32.OpenClipboard.argtypes = [wintypes.HWND]
    u32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]

    def put(fmt, data):
        h = k32.GlobalAlloc(0x0002, len(data))          # GMEM_MOVEABLE
        p = k32.GlobalLock(h)
        ctypes.memmove(p, data, len(data))
        k32.GlobalUnlock(h)
        u32.SetClipboardData(fmt, h)

    for _ in range(10):
        if u32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        return False
    try:
        u32.EmptyClipboard()
        put(13, text.encode("utf-16-le") + b"\x00\x00")   # CF_UNICODETEXT
        if html_fragment:
            head = ("Version:0.9\r\nStartHTML:{0:010d}\r\nEndHTML:{1:010d}\r\n"
                    "StartFragment:{2:010d}\r\nEndFragment:{3:010d}\r\n")
            pre, post = "<html><body><!--StartFragment-->", "<!--EndFragment--></body></html>"
            sh = len(head.format(0, 0, 0, 0).encode())
            sf = sh + len(pre.encode())
            ef = sf + len(html_fragment.encode("utf-8"))
            eh = ef + len(post.encode())
            payload = head.format(sh, eh, sf, ef) + pre + html_fragment + post
            put(u32.RegisterClipboardFormatW("HTML Format"), payload.encode("utf-8") + b"\x00")
        return True
    finally:
        u32.CloseClipboard()


# ---------------------------------------------------------------------------
class ScrollFrame(tk.Frame):
    """A vertically scrolling frame; the mouse wheel scrolls whichever one is under the pointer."""

    def __init__(self, master, bg=BG):
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.win, width=e.width))
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _wheel(self, e):
        self.canvas.yview_scroll(int(-e.delta / 120), "units")
