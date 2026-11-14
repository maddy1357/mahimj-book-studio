"""
Book Studio - one window for the whole KDP lifecycle.

  1 Book & Preview   build / import a book, preview every page, KDP print check
  2 AI Images        picture + text AI settings, generate / regenerate pictures
  3 Canva Design     Canva cover kit and checked cover import
  4 KDP Copy Sheet   every KDP field with a Copy button, store prices
  5 Upload to KDP    approve, then the uploader fills KDP in Edge as a draft
  6 Next Book Ideas  AI ideas, duplicate check, change / approve -> new book; growth tips

Start with:  python app.py   (or run.bat / the desktop shortcut)
"""
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, simpledialog, ttk

import pymupdf
from PIL import Image, ImageTk

from .. import canva, config
from .. import ideas as book_ideas
from ..ai import images as ai_images
from ..books import build as book_build
from ..books.alphabet import image_path
from ..books.alphabet_art import LETTERS
from ..config import BRAND_DIR, READY, ROOT
from ..kdp import copy_sheet
from .widgets import BG, BRAND, CARD, CHIP, FONT, INK, LINE, MUTED, OK, ScrollFrame, set_clipboard

LETTER_WORDS = [(letter, word.capitalize()) for letter, word, _ in LETTERS]
KDP_DETAILS_URL = "https://kdp.amazon.com/en_US/title-setup/paperback/new/details?ref_=cr_ti"
FIRST_BOOK = "alphabet-colouring-book"     # built automatically on first start


class Studio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("mahimj-books • Book Studio")
        self.geometry("1320x860")
        self.minsize(1050, 700)
        self.configure(bg=BG)
        try:
            self.iconbitmap(os.path.join(BRAND_DIR, "app.ico"))
        except Exception:
            pass
        self.book_dir, self.listing, self.docs = None, {}, {}
        self.thumbs, self.logq, self.uiq, self.uploading = [], queue.Queue(), queue.Queue(), False

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", font=(FONT, 11, "bold"), padding=(18, 8), background="#DDE3EE")
        style.map("TNotebook.Tab", background=[("selected", CARD)], foreground=[("selected", BRAND)])

        self._header()
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=12, pady=(8, 0))
        self.tab_book = tk.Frame(self.nb, bg=BG)
        self.tab_ai = tk.Frame(self.nb, bg=BG)
        self.tab_canva = tk.Frame(self.nb, bg=BG)
        self.tab_sheet = tk.Frame(self.nb, bg=BG)
        self.tab_upload = tk.Frame(self.nb, bg=BG)
        self.tab_ideas = tk.Frame(self.nb, bg=BG)
        self.nb.add(self.tab_book, text=" 1  Book & Preview ")
        self.nb.add(self.tab_ai, text=" 2  AI Images ")
        self.nb.add(self.tab_canva, text=" 3  Canva Design ")
        self.nb.add(self.tab_sheet, text=" 4  KDP Copy Sheet ")
        self.nb.add(self.tab_upload, text=" 5  Upload to KDP ")
        self.nb.add(self.tab_ideas, text=" 6  \U0001F4A1 Next Book Ideas ")
        self.gen_stop = False
        self.generating = False
        self.items = {}
        self._build_book_tab()
        self._build_ai_tab()
        self._build_canva_tab()
        self._build_sheet_tab()
        self._build_upload_tab()
        self._build_ideas_tab()

        self.status = tk.Label(self, text="", bg=BG, fg=MUTED, font=(FONT, 10), anchor="w")
        self.status.pack(fill="x", padx=16, pady=6)
        self.after(150, self._pump_log)
        self.after(50, self.refresh_books)

    # ------------------------------------------------------------------ header
    def _header(self):
        top = tk.Frame(self, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        top.pack(fill="x")
        self.brand_imgs = []
        for name, h in (("logo.png", 44), ("name.png", 28)):
            path = os.path.join(BRAND_DIR, name)
            if os.path.exists(path):
                im = Image.open(path).convert("RGBA")
                im = im.crop(im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox())
                im = im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
                self.brand_imgs.append(ImageTk.PhotoImage(im))
                tk.Label(top, image=self.brand_imgs[-1], bg=CARD).pack(side="left", padx=(14, 0), pady=8)
        tk.Label(top, text="Books  •  Book Studio", fg="#3A3A3A", bg=CARD, font=(FONT, 16)).pack(side="left", padx=10)
        self.book_var = tk.StringVar()
        self.book_box = ttk.Combobox(top, textvariable=self.book_var, state="readonly", width=34)
        self.book_box.pack(side="right", padx=16)
        self.book_box.bind("<<ComboboxSelected>>", lambda e: self.load_book())
        tk.Label(top, text="Book:", fg=INK, bg=CARD, font=(FONT, 11)).pack(side="right")

    def button(self, parent, text, cmd, primary=False, **kw):
        return tk.Button(parent, text=text, command=cmd, font=(FONT, 10, "bold" if primary else "normal"),
                         bg=BRAND if primary else CARD, fg="white" if primary else INK,
                         activebackground="#1D3FA8" if primary else CHIP, relief="flat", bd=0,
                         padx=14, pady=7, cursor="hand2", highlightthickness=1, highlightbackground=LINE, **kw)

    # ------------------------------------------------------------------ tab 1
    def _build_book_tab(self):
        t = self.tab_book
        bar = tk.Frame(t, bg=BG)
        bar.pack(fill="x", pady=(10, 6))
        self.button(bar, "↻  Rebuild book", self.rebuild).pack(side="left")
        self.button(bar, "Open PDFs", self.open_pdfs).pack(side="left", padx=6)
        self.button(bar, "Open folder", lambda: os.startfile(self.book_dir)).pack(side="left")
        self.button(bar, "\U0001F4E5  Import a book PDF\u2026", self.import_pdf).pack(side="left", padx=6)
        self.rights_btn = self.button(bar, "Confirm rights\u2026", self.confirm_rights)
        self.button(bar, "Next: KDP Copy Sheet  →", lambda: self.nb.select(self.tab_sheet), primary=True).pack(side="right")

        body = tk.Frame(t, bg=BG)
        body.pack(fill="both", expand=True)
        left = tk.Frame(body, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        left.pack(side="left", fill="both", expand=True)
        self.big_title = tk.Label(left, text="", bg=CARD, fg=INK, font=(FONT, 11, "bold"))
        self.big_title.pack(pady=(8, 2))
        self.big = tk.Label(left, bg=CARD)
        self.big.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        right = tk.Frame(body, bg=BG, width=440)
        right.pack(side="right", fill="y", padx=(12, 0))
        right.pack_propagate(False)
        self.info = tk.Label(right, text="", justify="left", anchor="w", bg=BG, fg=INK, font=(FONT, 10), wraplength=420)
        self.info.pack(fill="x", pady=(0, 6))
        self.thumb_area = ScrollFrame(right)
        self.thumb_area.pack(fill="both", expand=True)

    # ------------------------------------------------------------------ AI images tab
    def _build_ai_tab(self):
        t = self.tab_ai
        s = config.load_settings()
        card = tk.Frame(t, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        card.pack(fill="x", pady=(10, 8))
        g = tk.Frame(card, bg=CARD)
        g.pack(fill="x", padx=14, pady=10)
        lab = lambda r, c, txt: tk.Label(g, text=txt, bg=CARD, fg=INK, font=(FONT, 10, "bold")).grid(
            row=r, column=c, sticky="w", padx=(0, 6), pady=3)
        self.ai_label_to_key = {v: k for k, v in ai_images.PROVIDER_LABELS.items()}
        self.ai_provider = tk.StringVar(value=ai_images.PROVIDER_LABELS.get(s["provider"], s["provider"]))
        self.ai_model = tk.StringVar(value=s["openai_model"])
        self.ai_quality = tk.StringVar(value=s["openai_quality"])
        self.ai_okey = tk.StringVar(value=s["openai_key"])
        self.ai_skey = tk.StringVar(value=s["stability_key"])
        self.ai_cfacc = tk.StringVar(value=s["cf_account_id"])
        self.ai_cftok = tk.StringVar(value=s["cf_token"])
        self.ai_hftok = tk.StringVar(value=s["hf_token"])
        ent = lambda var, r, c, w, span=1, secret=True: tk.Entry(
            g, textvariable=var, show="•" if secret else "", width=w, font=(FONT, 10)).grid(
            row=r, column=c, columnspan=span, sticky="w", pady=3)
        link = lambda txt, url, r, c: tk.Button(g, text=txt, command=lambda: webbrowser.open(url), font=(FONT, 9),
                                                fg=BRAND, bg=CARD, relief="flat", cursor="hand2").grid(row=r, column=c, sticky="w")
        lab(0, 0, "AI service")
        ttk.Combobox(g, textvariable=self.ai_provider, values=list(ai_images.PROVIDER_LABELS.values()),
                     state="readonly", width=38).grid(row=0, column=1, columnspan=2, sticky="w")
        self.button(g, "Save settings", self.save_ai_settings).grid(row=0, column=5, sticky="e")
        lab(1, 0, "Cloudflare Account ID")
        ent(self.ai_cfacc, 1, 1, 36, secret=False)
        lab(1, 2, "API token")
        ent(self.ai_cftok, 1, 3, 40)
        link("Get free Cloudflare key ↗", "https://dash.cloudflare.com/profile/api-tokens", 1, 4)
        lab(2, 0, "Hugging Face token")
        ent(self.ai_hftok, 2, 1, 36)
        link("Get free HF token ↗", "https://huggingface.co/settings/tokens", 2, 2)
        lab(3, 0, "OpenAI key (paid)")
        ent(self.ai_okey, 3, 1, 36)
        lab(3, 2, "Model / quality")
        tk.Entry(g, textvariable=self.ai_model, width=16, font=(FONT, 10)).grid(row=3, column=3, sticky="w")
        ttk.Combobox(g, textvariable=self.ai_quality, values=["low", "medium", "high"], state="readonly",
                     width=8).grid(row=3, column=3, sticky="e")
        lab(3, 4, "Stability key (paid)")
        ent(self.ai_skey, 3, 5, 22)
        self.llm_labels = {"cloudflare": "Cloudflare \u2013 Llama 3.3 (free)", "claude": "Claude Opus 5.5 (best, paid)"}
        self.llm_provider = tk.StringVar(value=self.llm_labels.get(s.get("llm_provider", "cloudflare")))
        self.ai_anthkey = tk.StringVar(value=s.get("anthropic_key", ""))
        lab(5, 0, "Text AI (listings, ideas)")
        ttk.Combobox(g, textvariable=self.llm_provider, values=list(self.llm_labels.values()), state="readonly",
                     width=30).grid(row=5, column=1, sticky="w")
        lab(5, 2, "Anthropic API key")
        ent(self.ai_anthkey, 5, 3, 40)
        link("Get Anthropic key \u2197", "https://platform.claude.com/settings/keys", 5, 4)
        lab(4, 0, "Prompt ({word})")
        self.ai_style = tk.Text(g, height=3, width=110, wrap="word", font=(FONT, 9), bg=CHIP, relief="flat")
        self.ai_style.insert("1.0", s["prompt_style"])
        self.ai_style.grid(row=4, column=1, columnspan=5, sticky="we", pady=3)
        tk.Label(card, text=f"Keys are saved only on this computer for your Windows user ({config.SETTINGS_PATH}). "
                            "Each picture is billed by the provider you choose.",
                 bg=CARD, fg=MUTED, font=(FONT, 9), anchor="w").pack(fill="x", padx=14, pady=(0, 8))

        bar = tk.Frame(t, bg=BG)
        bar.pack(fill="x", pady=(0, 6))
        self.art_source = tk.StringVar(value="vector")
        tk.Label(bar, text="Pictures in the book:", bg=BG, fg=INK, font=(FONT, 10, "bold")).pack(side="left")
        for val, txt in (("vector", "Original drawings"), ("ai", "AI images")):
            tk.Radiobutton(bar, text=txt, value=val, variable=self.art_source, bg=BG, font=(FONT, 10),
                           command=self.set_art_source).pack(side="left", padx=6)
        self.button(bar, "✨  Recreate book with AI", self.recreate_with_ai, primary=True).pack(side="right")
        self.button(bar, "↻  Rebuild book", self.rebuild).pack(side="right", padx=6)
        self.button(bar, "Stop", self.stop_generation).pack(side="right")
        self.button(bar, "Regenerate all", lambda: self.generate(all_letters=True)).pack(side="right")
        self.button(bar, "Generate missing", lambda: self.generate(all_letters=False)).pack(side="right", padx=6)
        self.ai_status = tk.Label(t, text="", bg=BG, fg=MUTED, font=(FONT, 10), anchor="w")
        self.ai_status.pack(fill="x")
        self.ai_grid = ScrollFrame(t)
        self.ai_grid.pack(fill="both", expand=True, pady=(4, 0))
        self.ai_cells = {}

    def save_ai_settings(self, quiet=False):
        s = config.load_settings()
        s.update(provider=self.ai_label_to_key.get(self.ai_provider.get(), "cloudflare"),
                 cf_account_id=self.ai_cfacc.get().strip(), cf_token=self.ai_cftok.get().strip(),
                 hf_token=self.ai_hftok.get().strip(),
                 openai_model=self.ai_model.get().strip() or "gpt-image-1",
                 openai_quality=self.ai_quality.get(), openai_key=self.ai_okey.get().strip(),
                 stability_key=self.ai_skey.get().strip(), prompt_style=self.ai_style.get("1.0", "end").strip(),
                 llm_provider={v: k for k, v in self.llm_labels.items()}.get(self.llm_provider.get(), "cloudflare"),
                 anthropic_key=self.ai_anthkey.get().strip())
        config.save_settings(s)
        if not quiet:
            self.ai_status.configure(text="Settings saved.")
        return s

    def set_art_source(self):
        cfg = config.book_config(self.book_dir)
        cfg["art_source"] = self.art_source.get()
        config.save_book_config(self.book_dir, cfg)
        self.ai_status.configure(text="Saved. Press 'Rebuild book' to apply it to the PDF.")

    def art_items(self):
        """(key, label, word, path, colour) for every picture this book uses."""
        kind = book_build.builder_of(self.book_dir)
        if kind == "theme":
            from ..books import theme as T
            spec = T.load_spec(self.book_dir)
            subj = spec["page_subjects"]
            items = [(f"{i + 1:02d}", f"{i + 1}. {w}", w, T.pic(self.book_dir, i), False) for i, w in enumerate(subj)]
            return items + [(f"cover-{i + 1}", f"Cover: {subj[i]}", subj[i], T.cover_pic(self.book_dir, i), True)
                            for i in range(min(6, len(subj)))]
        if kind == "imported":
            return []
        return [(l, f"{l}  {w}", w, image_path(self.book_dir, l), False) for l, w in LETTER_WORDS]

    def fill_ai_grid(self):
        inner = self.ai_grid.inner
        for w in inner.winfo_children():
            w.destroy()
        self.ai_cells, self.ai_imgs = {}, {}
        self.items = {it[0]: it for it in self.art_items()}
        kind = book_build.builder_of(self.book_dir)
        self.art_source.set(config.book_config(self.book_dir).get("art_source", "vector"))
        if kind == "imported":
            tk.Label(inner, text="This book was imported from a PDF - its pictures come from that file.",
                     bg=BG, fg=MUTED, font=(FONT, 11)).grid(row=0, column=0, pady=30, padx=20)
        for i, (key, label, word, path, color) in enumerate(self.items.values()):
            cell = tk.Frame(inner, bg=CARD, highlightthickness=1, highlightbackground=LINE)
            cell.grid(row=i // 7, column=i % 7, padx=5, pady=5, sticky="n")
            pic = tk.Label(cell, bg=CARD, width=130, height=130)
            pic.pack(padx=6, pady=(6, 2))
            tk.Label(cell, text=label[:22], bg=CARD, fg=INK, font=(FONT, 9, "bold")).pack()
            b = tk.Button(cell, text="Generate", font=(FONT, 9), relief="flat", bg=CHIP, cursor="hand2",
                          command=lambda k=key: self.generate(only=[k]))
            b.pack(fill="x", padx=6, pady=(2, 6))
            self.ai_cells[key] = (pic, b)
            self.refresh_ai_cell(key)
        self.update_ai_count()

    def refresh_ai_cell(self, key):
        if key not in self.ai_cells:
            return
        pic, b = self.ai_cells[key]
        p = self.items[key][3]
        if os.path.exists(p):
            im = Image.open(p)
            im.thumbnail((130, 130))
            self.ai_imgs[key] = ImageTk.PhotoImage(im)
            pic.configure(image=self.ai_imgs[key], text="", width=130, height=130)
            b.configure(text="Regenerate")
        else:
            if not hasattr(self, "_placeholder"):
                from PIL import ImageDraw
                ph = Image.new("RGB", (130, 130), CHIP)
                ImageDraw.Draw(ph).text((22, 58), "no AI image yet", fill=MUTED)
                self._placeholder = ImageTk.PhotoImage(ph)
            pic.configure(image=self._placeholder, width=130, height=130)
            b.configure(text="Generate")

    def update_ai_count(self):
        if self.generating or not self.items:
            return
        have = sum(os.path.exists(it[3]) for it in self.items.values())
        extra = "" if book_build.builder_of(self.book_dir) == "theme" else " Letters without one use the original drawing."
        self.ai_status.configure(text=f"{have} / {len(self.items)} AI images ready.{extra}")

    def stop_generation(self):
        self.gen_stop = True

    def recreate_with_ai(self):
        """One click: generate every missing picture, switch the book to AI art, rebuild."""
        self.generate(all_letters=False, then_rebuild=True)

    def generate(self, all_letters=False, only=None, then_rebuild=False):
        if self.generating or not self.items:
            return
        s = self.save_ai_settings(quiet=True)
        if only:
            todo = [self.items[k] for k in only]
        elif all_letters:
            if not messagebox.askyesno("Regenerate all", f"Generate all {len(self.items)} pictures again?"):
                return
            todo = list(self.items.values())
        else:
            todo = [it for it in self.items.values() if not os.path.exists(it[3])]
        if not todo:
            if then_rebuild:
                self.art_source.set("ai")
                self.set_art_source()
                self.rebuild()
                self.nb.select(self.tab_book)
                return
            self.ai_status.configure(text="All AI images already exist. Use Regenerate on any you want to change.")
            return
        self.generating, self.gen_stop = True, False

        def work():
            done_n = 0
            for key, label, word, path, color in todo:
                if self.gen_stop:
                    break
                self.ui(lambda l=label, n=done_n: self.ai_status.configure(
                    text=f"Generating {l}  ({n + 1}/{len(todo)}) ..."))
                try:
                    ai_images.generate_image(path, word, s, color=color)
                    done_n += 1
                    self.ui(lambda k=key: self.refresh_ai_cell(k))
                except Exception as e:
                    msg = str(e)
                    self.ui(lambda m=msg: messagebox.showerror("Image generation failed", m))
                    break

            def finish():
                self.generating = False
                self.update_ai_count()
                if done_n and self.art_source.get() != "ai":
                    self.art_source.set("ai")
                    self.set_art_source()
                if done_n and then_rebuild and not self.gen_stop and done_n == len(todo):
                    self.ai_status.configure(text="All pictures ready - rebuilding the book...")
                    self.rebuild()
                    self.nb.select(self.tab_book)
                elif done_n:
                    self.ai_status.configure(text=self.ai_status.cget("text") + "  Press 'Rebuild book' to use them.")
            self.ui(finish)
        threading.Thread(target=work, daemon=True).start()

    # ------------------------------------------------------------------ Canva tab
    def _build_canva_tab(self):
        t = self.tab_canva
        card = tk.Frame(t, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        card.pack(fill="x", pady=(10, 8))
        self.canva_info = tk.Label(card, text="", bg=CARD, fg=INK, font=(FONT, 10), justify="left", anchor="w")
        self.canva_info.pack(fill="x", padx=14, pady=(12, 6))
        steps = ("1  Make Canva kit – exact-size KDP cover guide, the current cover, your logos and every picture in colour.\n"
                 "2  In Canva: Create a design → Custom size (inches, size above). Upload the kit, design, then delete the guide layer.\n"
                 "3  Share → Download → PDF Print, tick 'Flatten PDF', do NOT tick 'Crop marks and bleed'.\n"
                 "4  Import cover PDF from Canva – the app checks the size against KDP and rebuilds the book with it.")
        tk.Label(card, text=steps, bg=CARD, fg=MUTED, font=(FONT, 10), justify="left", anchor="w").pack(fill="x", padx=14)
        bar = tk.Frame(card, bg=CARD)
        bar.pack(fill="x", padx=14, pady=12)
        self.button(bar, "1  Make Canva kit", self.make_canva_kit, primary=True).pack(side="left")
        self.button(bar, "2  Open Canva", lambda: webbrowser.open("https://www.canva.com/")).pack(side="left", padx=6)
        self.button(bar, "4  Import cover PDF from Canva", self.import_canva_cover, primary=True).pack(side="left")
        self.button(bar, "Use the app's cover instead", self.use_app_cover).pack(side="left", padx=6)
        self.canva_preview = tk.Label(t, bg=BG)
        self.canva_preview.pack(fill="both", expand=True, pady=6)

    def refresh_canva_tab(self):
        try:
            W, H, spine = canva.cover_size(self.book_dir)
        except Exception:
            return
        src = config.book_config(self.book_dir).get("cover_source", "generated")
        self.canva_info.configure(text=(
            f"Canva design size (full wrap with bleed):  {W:.3f} in  x  {H:.3f} in      spine {spine:.4f} in\n"
            f"Cover in use:  {'Canva design (imported)' if src == 'canva' else 'made by this app'}"))
        self.update_idletasks()
        w = max(600, self.tab_canva.winfo_width() - 40)
        img = self.render(os.path.join(self.book_dir, "cover.pdf"), 0, w, 430)
        self.canva_img = ImageTk.PhotoImage(img)
        self.canva_preview.configure(image=self.canva_img)

    def make_canva_kit(self):
        self.set_status("Making Canva kit...")
        try:
            kit = canva.make_kit(self.book_dir)
        except Exception as e:
            messagebox.showerror("Canva kit", str(e))
            return
        self.set_status(f"Canva kit ready: {kit}")
        os.startfile(kit)

    def import_canva_cover(self):
        path = filedialog.askopenfilename(title="Choose the cover PDF you downloaded from Canva",
                                          filetypes=[("PDF", "*.pdf")],
                                          initialdir=os.path.join(os.path.expanduser("~"), "Downloads"))
        if not path:
            return
        ok, msg = canva.import_cover(self.book_dir, path)
        (messagebox.showinfo if ok else messagebox.showerror)("Import cover", msg)
        if ok:
            self.rebuild()

    def use_app_cover(self):
        canva.use_generated_cover(self.book_dir)
        self.rebuild()

    # ------------------------------------------------------------------ tab 2
    def _build_sheet_tab(self):
        t = self.tab_sheet
        bar = tk.Frame(t, bg=BG)
        bar.pack(fill="x", pady=(10, 6))
        self.button(bar, "Open KDP (new paperback)", lambda: webbrowser.open(KDP_DETAILS_URL), primary=True).pack(side="left")
        self.button(bar, "Reset ticks", self.reset_ticks).pack(side="left", padx=6)
        self.progress = tk.Label(bar, text="", bg=BG, fg=MUTED, font=(FONT, 11, "bold"))
        self.progress.pack(side="right", padx=6)
        tk.Label(t, text="Copy a value, paste it into KDP with Ctrl+V. 'Select' rows are options you click in KDP. "
                         "Ticks are remembered for this book.", bg=BG, fg=MUTED, font=(FONT, 10), anchor="w").pack(fill="x")
        self.sheet = ScrollFrame(t)
        self.sheet.pack(fill="both", expand=True, pady=(6, 0))

    def fill_sheet(self):
        inner = self.sheet.inner
        for w in inner.winfo_children():
            w.destroy()
        self.checks = {}
        ticks = self._load_ticks()
        n = 0
        for step, title, rows in copy_sheet.build_sections(self.book_dir, self.listing):
            card = tk.Frame(inner, bg=CARD, highlightthickness=1, highlightbackground=LINE)
            card.pack(fill="x", padx=4, pady=(0, 14))
            head = tk.Frame(card, bg=CARD)
            head.pack(fill="x", padx=14, pady=10)
            tk.Label(head, text=f" {step} ", bg=BRAND, fg="white", font=(FONT, 10, "bold")).pack(side="left")
            tk.Label(head, text="  " + title, bg=CARD, fg=INK, font=(FONT, 13, "bold")).pack(side="left")
            for kind, label, value, note in rows:
                n += 1
                key = f"f{n}"
                tk.Frame(card, bg=LINE, height=1).pack(fill="x")
                row = tk.Frame(card, bg=CARD)
                row.pack(fill="x", padx=14, pady=7)
                var = tk.BooleanVar(value=bool(ticks.get(key)))
                self.checks[key] = var
                tk.Checkbutton(row, variable=var, bg=CARD, activebackground=CARD,
                               command=self._save_ticks).grid(row=0, column=0, sticky="nw")
                tk.Label(row, text=label, bg=CARD, fg=INK, font=(FONT, 10, "bold"), width=24, anchor="nw",
                         justify="left").grid(row=0, column=1, sticky="nw", pady=3)
                plain = copy_sheet.strip_html(value) if kind == "rich" else value
                if kind == "rich":
                    box = tk.Text(row, height=9, wrap="word", bg=CHIP, fg=INK, font=(FONT, 10), relief="flat",
                                  padx=8, pady=6)
                    box.insert("1.0", plain)
                    box.configure(state="disabled")
                else:
                    box = tk.Entry(row, bg=CHIP, fg=INK, font=(FONT, 10), relief="flat",
                                   readonlybackground=CHIP)
                    box.insert(0, plain)
                    box.configure(state="readonly")
                box.grid(row=0, column=2, sticky="ew", padx=8, ipady=4)
                if note:
                    tk.Label(row, text=note, bg=CARD, fg=MUTED, font=(FONT, 9), anchor="w", justify="left",
                             wraplength=640).grid(row=1, column=2, sticky="w", padx=8)
                if kind in ("copy", "rich"):
                    b = tk.Button(row, text="Copy", width=10, font=(FONT, 10, "bold"), bg=BRAND, fg="white",
                                  activebackground="#1D3FA8", relief="flat", cursor="hand2")
                    b.configure(command=lambda b=b, k=key, pl=plain, h=(value if kind == "rich" else None):
                                self.copy(b, k, pl, h))
                    b.grid(row=0, column=3, sticky="ne")
                elif kind == "link":
                    tk.Button(row, text="Open ↗", width=10, font=(FONT, 10, "bold"), bg="#14B8D4", fg="#04222b",
                              relief="flat", cursor="hand2",
                              command=lambda u=value: webbrowser.open(u)).grid(row=0, column=3, sticky="ne")
                else:
                    tk.Label(row, text="Select" if kind == "choice" else "Info", width=10, bg=CARD, fg=MUTED,
                             font=(FONT, 9), relief="groove").grid(row=0, column=3, sticky="ne", ipady=3)
                row.columnconfigure(2, weight=1)
        self._update_progress()

    def copy(self, btn, key, text, html_fragment):
        ok = set_clipboard(text, html_fragment, self)
        btn.configure(text="Copied ✓" if ok else "Retry", bg=OK if ok else "#B23B3B")
        if ok:
            self.checks[key].set(True)
            self._save_ticks()
        self.after(1400, lambda: btn.configure(text="Copy", bg=BRAND))

    def _ticks_path(self):
        return os.path.join(self.book_dir, "kdp-progress.json")

    def _load_ticks(self):
        return config.read_json(self._ticks_path(), {})

    def _save_ticks(self):
        config.write_json(self._ticks_path(), {k: v.get() for k, v in self.checks.items() if v.get()})
        self._update_progress()

    def _update_progress(self):
        d = sum(v.get() for v in self.checks.values())
        self.progress.configure(text=f"{d} / {len(self.checks)} done")

    def reset_ticks(self):
        if messagebox.askyesno("Reset", "Clear all ticks for this book?"):
            for v in self.checks.values():
                v.set(False)
            self._save_ticks()

    # ------------------------------------------------------------------ tab 3
    def _build_upload_tab(self):
        t = self.tab_upload
        card = tk.Frame(t, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        card.pack(fill="x", pady=(10, 8))
        txt = ("Approve & Upload opens Amazon KDP in a separate Edge window. Sign in there yourself – "
               "your password is never seen or stored by this app.\n"
               "The uploader fills title, subtitle, author, description, keywords and rights, saves a DRAFT, "
               "then uploads interior.pdf and cover.pdf on the Content page.\n"
               "It never assigns the ISBN and never presses Publish – finish those from the KDP Copy Sheet tab.")
        tk.Label(card, text=txt, bg=CARD, fg=INK, font=(FONT, 10), justify="left", anchor="w",
                 wraplength=1150).pack(fill="x", padx=14, pady=(12, 8))
        bar = tk.Frame(card, bg=CARD)
        bar.pack(fill="x", padx=14, pady=(0, 12))
        self.approve_btn = tk.Button(bar, text="✔  Approve & Upload to KDP", command=self.approve,
                                     font=(FONT, 11, "bold"), bg=OK, fg="white", activebackground="#25A56A",
                                     relief="flat", padx=16, pady=8, cursor="hand2")
        self.approve_btn.pack(side="left")
        self.button(bar, "Open KDP in my browser", lambda: webbrowser.open(KDP_DETAILS_URL)).pack(side="left", padx=8)
        self.upload_state = tk.Label(bar, text="", bg=CARD, fg=MUTED, font=(FONT, 10, "bold"))
        self.upload_state.pack(side="left", padx=10)
        tk.Label(t, text="Upload log", bg=BG, fg=INK, font=(FONT, 11, "bold"), anchor="w").pack(fill="x")
        wrap = tk.Frame(t, bg=BG)
        wrap.pack(fill="both", expand=True, pady=(4, 0))
        self.log = tk.Text(wrap, bg="#0F1626", fg="#D7E0F0", insertbackground="white", font=("Consolas", 10),
                           relief="flat", padx=10, pady=8, state="disabled")
        sb = ttk.Scrollbar(wrap, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.log.tag_configure("ok", foreground="#6EE7A8")
        self.log.tag_configure("todo", foreground="#FFD27A")

    def write_log(self, line):
        self.log.configure(state="normal")
        tag = "ok" if " OK " in line or "[x]" in line else ("todo" if "TODO" in line or "[ ]" in line else "")
        self.log.insert("end", line + "\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def ui(self, fn):
        """Thread-safe: run fn on the Tk main thread (workers must never touch widgets directly)."""
        self.uiq.put(fn)

    def _pump_log(self):
        try:
            while True:
                self.write_log(self.logq.get_nowait())
        except queue.Empty:
            pass
        try:
            while True:
                self.uiq.get_nowait()()
        except queue.Empty:
            pass
        self.after(100, self._pump_log)

    # ------------------------------------------------------------------ data
    def set_status(self, msg):
        self.status.configure(text=msg)
        self.update_idletasks()

    def refresh_books(self):
        os.makedirs(READY, exist_ok=True)
        if not any(os.path.exists(os.path.join(READY, d, "kdp-listing.json")) for d in os.listdir(READY)):
            self.set_status("Building the first book...")
            self.run_build(os.path.join(READY, FIRST_BOOK))
        books = sorted(d for d in os.listdir(READY) if os.path.exists(os.path.join(READY, d, "kdp-listing.json")))
        self.book_box["values"] = books
        if books:
            if self.book_var.get() not in books:
                self.book_var.set(books[0])
            self.load_book()
        else:
            self.set_status("No books found in ready-to-publish/")

    def run_build(self, book_dir):
        r = subprocess.run([sys.executable, "-m", "studio.books.build", book_dir], cwd=ROOT, capture_output=True,
                           text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode != 0:
            err = r.stderr[-1500:]
            self.ui(lambda: messagebox.showerror("Build failed", err))
        return r.returncode == 0

    def doc(self, path):
        mt = os.path.getmtime(path)
        if path not in self.docs or self.docs[path][0] != mt:
            # read into memory so the file is never locked (Windows) while the book is rebuilt
            with open(path, "rb") as f:
                self.docs[path] = (mt, pymupdf.open(stream=f.read(), filetype="pdf"))
        return self.docs[path][1]

    def render(self, path, index, max_w, max_h):
        pg = self.doc(path)[index]
        z = min(max_w / pg.rect.width, max_h / pg.rect.height)
        pix = pg.get_pixmap(matrix=pymupdf.Matrix(z, z))
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    def load_book(self):
        self.book_dir = os.path.join(READY, self.book_var.get())
        self.listing = config.load_listing(self.book_dir)
        L, p = self.listing, self.listing["print"]
        pf = L.get("preflight", {})
        self.info.configure(text=(
            f"{L['title']}\n{L['subtitle']}\n\n"
            f"Author: {L['author']}     Imprint: {L['publisher_imprint']}\n"
            f"{p['page_count']} pages • {p['trim_size']} • {p['ink_and_paper']}\n"
            + ("Single-sided: blank back behind every picture\n" if p.get("single_sided") else "")
            + ("KDP print check: PASSED ✔\n" if pf.get("passed")
               else "KDP print check: PROBLEMS\n  - " + "\n  - ".join(pf.get("problems", ["not run"])) + "\n")
            + "".join(f"  ! {w}\n" for w in pf.get("warnings", [])[:4])
            + f"Type: {L.get('book_type', 'alphabet')}   Price: ${L.get('price_usd_suggested', '')}\n"
            + f"Status: {L.get('status', '?').replace('_', ' ').upper()}\n\nClick a thumbnail to view it large."))
        if L.get("rights_flags") and not L.get("rights_confirmed"):
            self.rights_btn.pack(side="left", padx=6)
        else:
            self.rights_btn.pack_forget()
        inner = self.thumb_area.inner
        for w in inner.winfo_children():
            w.destroy()
        self.thumbs = []
        interior = os.path.join(self.book_dir, "interior.pdf")
        cover = os.path.join(self.book_dir, "cover.pdf")
        items = [("Cover", cover, 0)] + [(f"Page {i + 1}", interior, i) for i in range(len(self.doc(interior)))]
        for n, (label, pdf, idx) in enumerate(items):
            img = ImageTk.PhotoImage(self.render(pdf, idx, 250 if n == 0 else 118, 150))
            self.thumbs.append(img)
            cell = tk.Frame(inner, bg=BG)
            if n == 0:
                cell.grid(row=0, column=0, columnspan=3, pady=6)
            else:
                cell.grid(row=1 + (n - 1) // 3, column=(n - 1) % 3, padx=6, pady=6)
            b = tk.Label(cell, image=img, bd=1, relief="solid", cursor="hand2")
            b.pack()
            b.bind("<Button-1>", lambda e, a=(label, pdf, idx): self.show(*a))
            tk.Label(cell, text=label, bg=BG, fg=MUTED, font=(FONT, 8)).pack()
        self.after(60, lambda: self.show("Cover", cover, 0))
        self.fill_ai_grid()
        self.after(80, self.refresh_canva_tab)
        self.fill_sheet()
        self.update_upload_state()
        self.set_status(f"Book folder: {self.book_dir}")

    def show(self, label, pdf, idx):
        self.update_idletasks()
        w = max(420, self.big.winfo_width() - 10)
        h = max(420, self.big.winfo_height() - 10)
        self.big_img = ImageTk.PhotoImage(self.render(pdf, idx, w, h))
        self.big.configure(image=self.big_img)
        self.big_title.configure(text=label)

    def update_upload_state(self):
        st = self.listing.get("status", "")
        passed = self.listing.get("preflight", {}).get("passed")
        if self.uploading:
            self.approve_btn.configure(state="disabled", text="Uploading...")
        elif not passed:
            self.approve_btn.configure(state="disabled", text="Fix print-check problems first")
        else:
            self.approve_btn.configure(state="normal",
                                       text="↻  Upload again" if st == "uploaded_draft" else "✔  Approve & Upload to KDP")
        self.upload_state.configure(text=f"Status: {st.replace('_', ' ').upper()}")

    # ------------------------------------------------------------------ actions
    def rebuild(self):
        self.set_status("Rebuilding the book...")
        self.config(cursor="watch")

        book_dir = self.book_dir

        def work():
            ok = self.run_build(book_dir)
            self.ui(lambda: (self.config(cursor=""), ok and self.load_book(),
                                   self.set_status("Rebuilt." if ok else "Build failed.")))
        threading.Thread(target=work, daemon=True).start()

    def select_book(self, book_dir):
        self.book_var.set(os.path.basename(book_dir))
        self.refresh_books()
        self.nb.select(self.tab_book)

    def import_pdf(self):
        path = filedialog.askopenfilename(title="Choose a finished book PDF (interior)", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        desc = simpledialog.askstring("What is this book about?",
                                      "Optional: describe the book in one line (helps the AI write the listing).",
                                      parent=self) or ""
        s = self.save_ai_settings(quiet=True)
        self.set_status("Analysing the book with AI...")
        self.config(cursor="watch")

        def work():
            try:
                from ..books import importer as analyze_book
                bd = analyze_book.import_book(path, desc, s, log=lambda m: self.ui(lambda m=m: self.set_status(m)))
                self.ui(lambda: (self.config(cursor=""), self.select_book(bd)))
            except Exception as e:
                msg = str(e)
                self.ui(lambda: (self.config(cursor=""), messagebox.showerror("Import failed", msg)))
        threading.Thread(target=work, daemon=True).start()

    def confirm_rights(self):
        flags = "\n  - ".join(self.listing.get("rights_flags", []))
        if not messagebox.askyesno(
                "Do you own the rights?",
                f"This book mentions other names, websites or copyright notices:\n  - {flags}\n\n"
                "Publishing someone else's work without permission breaks KDP's rules and can close your account.\n\n"
                "Do you own this book, or have written permission to sell it commercially?", icon="warning"):
            return
        cfg = config.book_config(self.book_dir)
        cfg["rights_confirmed"] = True
        config.save_book_config(self.book_dir, cfg)
        self.rebuild()

    # ------------------------------------------------------------------ ideas tab
    def _build_ideas_tab(self):
        t = self.tab_ideas
        bar = tk.Frame(t, bg=BG)
        bar.pack(fill="x", pady=(10, 6))
        self.button(bar, "\U0001F4A1  Suggest 5 new books", self.suggest_ideas, primary=True).pack(side="left")
        self.button(bar, "Stop", self.stop_generation).pack(side="left", padx=6)
        self.ideas_status = tk.Label(bar, text="", bg=BG, fg=MUTED, font=(FONT, 10))
        self.ideas_status.pack(side="left", padx=10)
        tk.Label(t, text="Each idea is checked against your books and earlier ideas - a near-duplicate is replaced "
                         "automatically. Market notes are the AI's estimate, not live Amazon data.",
                 bg=BG, fg=MUTED, font=(FONT, 9), anchor="w").pack(fill="x")
        body = tk.Frame(t, bg=BG)
        body.pack(fill="both", expand=True, pady=(6, 0))
        side = tk.Frame(body, bg=CARD, width=360, highlightthickness=1, highlightbackground=LINE)
        side.pack(side="right", fill="y", padx=(10, 0))
        side.pack_propagate(False)
        self.ideas_list = ScrollFrame(body)
        self.ideas_list.pack(side="left", fill="both", expand=True)
        tk.Label(side, text="How to get more buyers", bg=CARD, fg=BRAND, font=(FONT, 13, "bold")).pack(
            anchor="w", padx=12, pady=(12, 6))
        for tip in book_ideas.GROWTH_PLAYBOOK:
            tk.Label(side, text="• " + tip, bg=CARD, fg=INK, font=(FONT, 9), wraplength=330, justify="left",
                     anchor="w").pack(fill="x", padx=12, pady=3)
        self.fill_ideas()

    def fill_ideas(self):
        inner = self.ideas_list.inner
        for w in inner.winfo_children():
            w.destroy()
        shown = [i for i in reversed(book_ideas.load_ideas()) if i.get("status") != "replaced"]
        if not shown:
            tk.Label(inner, text="No ideas yet - press 'Suggest 5 new books'.\n"
                                 "It uses the Text AI chosen in the AI Images tab.",
                     bg=BG, fg=MUTED, font=(FONT, 11)).pack(pady=40)
        for idea in shown[:20]:
            card = tk.Frame(inner, bg=CARD, highlightthickness=1, highlightbackground=LINE)
            card.pack(fill="x", padx=4, pady=(0, 10))
            head = tk.Frame(card, bg=CARD)
            head.pack(fill="x", padx=12, pady=(10, 2))
            tk.Label(head, text=idea["title"], bg=CARD, fg=INK, font=(FONT, 13, "bold")).pack(side="left")
            dup = idea.get("duplicate_of")
            tk.Label(head, text=(f"⚠ similar to '{dup}'" if dup else "✔ new idea"), bg=CARD,
                     fg="#B26A00" if dup else OK, font=(FONT, 9, "bold")).pack(side="left", padx=10)
            if idea.get("status") == "approved" and idea.get("book_dir"):
                self.button(head, "Open book", lambda i=idea: self.select_book(os.path.join(READY, i["book_dir"]))
                            ).pack(side="right")
            else:
                self.button(head, "✔  Approve & create book", lambda i=idea: self.approve_idea(i),
                            primary=True).pack(side="right")
                self.button(head, "↻  Change idea", lambda i=idea: self.change_idea(i)).pack(side="right", padx=6)
            lines = [
                ("", idea.get("subtitle", "")),
                ("For: ", f"{idea.get('audience', '')}, ages {idea.get('age_min', '')}-{idea.get('age_max', '')} • "
                          f"{len(idea.get('page_subjects', []))} pictures • theme: {idea.get('theme', '')}"),
                ("Why it sells: ", idea.get("why_it_sells", "")),
                ("Different because: ", idea.get("differentiation", "")),
                ("Market (AI estimate): ", idea.get("market_note", "")),
                ("Pictures: ", ", ".join(idea.get("page_subjects", [])[:14]) + " …"),
                ("More buyers: ", " • ".join(idea.get("marketing", []))),
            ]
            for k, v in lines:
                tk.Label(card, text=k + v, bg=CARD, fg=INK if k else MUTED, font=(FONT, 9), wraplength=780,
                         justify="left", anchor="w").pack(fill="x", padx=12, pady=1)
            tk.Frame(card, bg=CARD, height=8).pack()

    def suggest_ideas(self):
        s = self.save_ai_settings(quiet=True)
        self.ideas_status.configure(text="Asking the AI for ideas (about a minute)...")

        def work():
            try:
                book_ideas.generate(5, s)
                self.ui(lambda: (self.ideas_status.configure(text="5 new ideas."), self.fill_ideas()))
            except Exception as e:
                msg = str(e)
                self.ui(lambda: (self.ideas_status.configure(text=""), messagebox.showerror("Ideas failed", msg)))
        threading.Thread(target=work, daemon=True).start()

    def change_idea(self, idea):
        reason = simpledialog.askstring("Change idea", "Optional: what don't you like about it?", parent=self) or ""
        s = self.save_ai_settings(quiet=True)
        self.ideas_status.configure(text="Changing the idea...")

        def work():
            try:
                book_ideas.change(idea, s, reason=reason)
                self.ui(lambda: (self.ideas_status.configure(text="Idea changed."), self.fill_ideas()))
            except Exception as e:
                msg = str(e)
                self.ui(lambda: (self.ideas_status.configure(text=""), messagebox.showerror("Change failed", msg)))
        threading.Thread(target=work, daemon=True).start()

    def approve_idea(self, idea):
        n = len(idea.get("page_subjects", []))
        if not messagebox.askyesno("Create this book?",
                                   f"Create \"{idea['title']}\"?\n\nThe app will generate {n} line-art pictures and "
                                   f"{min(6, n)} colour cover pictures with your AI image service, then build the "
                                   "book, cover, prices and copy sheet. You review everything before uploading."):
            return
        s = self.save_ai_settings(quiet=True)
        book_dir = book_ideas.create_book(idea)
        self.fill_ideas()
        self.gen_stop = False

        def work():
            from ..books import theme as T
            try:
                spec = T.load_spec(book_dir)
                ok = T.generate_images(book_dir, spec, s,
                                       log=lambda m: self.ui(lambda m=m: self.ideas_status.configure(text=m)),
                                       stop=lambda: self.gen_stop)
                if not ok:
                    self.ui(lambda: self.ideas_status.configure(text="Stopped. Approve again later to continue."))
                    return
                self.ui(lambda: self.ideas_status.configure(text="Building the book..."))
                if self.run_build(book_dir):
                    self.ui(lambda: (self.ideas_status.configure(text="Book created - review it, then upload."),
                                     self.select_book(book_dir)))
            except Exception as e:
                msg = str(e)
                self.ui(lambda: (self.ideas_status.configure(text="Stopped - finish it from the AI Images tab."),
                                 messagebox.showerror("Create book failed", msg)))
        threading.Thread(target=work, daemon=True).start()

    def open_pdfs(self):
        for f in ("interior.pdf", "cover.pdf"):
            os.startfile(os.path.join(self.book_dir, f))

    def approve(self):
        L = self.listing
        if not messagebox.askyesno(
                "Approve & upload",
                f"Approve \"{L['title']}\" by {L['author']} and upload it to Amazon KDP?\n\n"
                "An Edge window will open – sign in to KDP there yourself.\n"
                "The uploader saves a DRAFT and uploads the PDFs. It never presses Publish."):
            return
        L["status"] = "approved"
        L["approved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        config.save_listing(self.book_dir, L)
        self.uploading = True
        self.update_upload_state()
        book_dir = self.book_dir

        def work():
            try:
                from ..kdp import uploader as kdp_upload
                kdp_upload.run(book_dir, log_fn=self.logq.put)
            except Exception as e:
                self.logq.put(f"Uploader error: {e}")
            finally:
                def done():
                    self.uploading = False
                    if self.book_dir == book_dir:
                        self.listing = config.load_listing(book_dir)
                    self.update_upload_state()
                self.ui(done)
        threading.Thread(target=work, daemon=True).start()
        self.write_log("Approved. Starting uploader - sign in to KDP in the Edge window that opens.")


def main():
    Studio().mainloop()
