"""
Rebuild any book folder, whatever its type:

    python -m studio.books.build ready-to-publish/<book>

book-config.json "builder":  alphabet (the A-Z book) | theme (from an approved idea) | imported (a PDF you imported)
"""
import os
import sys

from ..config import book_config


def builder_of(book_dir):
    cfg = book_config(book_dir)
    if "builder" in cfg:
        return cfg["builder"]
    if os.path.exists(os.path.join(book_dir, "book-spec.json")):
        return "theme"
    return "alphabet"


def build(book_dir, log=print):
    kind = builder_of(book_dir)
    if kind == "theme":
        from . import theme
        return theme.build(book_dir, log=log)
    if kind == "imported":
        from . import importer
        return importer.rebuild(book_dir, log=log)
    from . import alphabet
    return alphabet.build(book_dir, log=log)


if __name__ == "__main__":
    build(os.path.abspath(sys.argv[1]))
