"""
mahimj-books :: rebuild any book folder, whatever its type.

  python tools/build.py ready-to-publish/<book>

book-config.json "builder":
  alphabet  -> build_alphabet_book.py   (the original A-Z book)
  theme     -> build_theme_book.py      (books created from an approved idea)
  imported  -> analyze_book.rebuild     (a PDF you imported)
"""
import os
import sys

import ai_images


def builder_of(book_dir):
    cfg = ai_images.book_config(book_dir)
    if "builder" in cfg:
        return cfg["builder"]
    if os.path.exists(os.path.join(book_dir, "book-spec.json")):
        return "theme"
    return "alphabet"


def build(book_dir, log=print):
    kind = builder_of(book_dir)
    if kind == "theme":
        import build_theme_book
        return build_theme_book.build(book_dir, log=log)
    if kind == "imported":
        import analyze_book
        return analyze_book.rebuild(book_dir, log=log)
    import build_alphabet_book
    sys.argv = [sys.argv[0], book_dir]
    return build_alphabet_book.main()


if __name__ == "__main__":
    build(os.path.abspath(sys.argv[1]))
