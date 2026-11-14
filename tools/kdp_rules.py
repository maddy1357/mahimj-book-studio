"""
mahimj-books :: KDP paperback rules used by every book type.

Numbers come from KDP's own pages/screens (checked Nov 2026) and are ESTIMATES
for planning - KDP's Rights & Pricing page always shows the exact figures.
"""
import math

BLEED_IN = 0.125
SPINE_PER_PAGE = {"white": 0.002252, "cream": 0.0025}
MIN_PAGES, MAX_PAGES_BW = 24, 828

# KDP paperback trim sizes (inches)
TRIMS = [(5, 8), (5.06, 7.81), (5.25, 8), (5.5, 8.5), (6, 9), (6.14, 9.21), (6.69, 9.61), (7, 10),
         (7.44, 9.69), (7.5, 9.25), (8, 10), (8.25, 6), (8.25, 8.25), (8.5, 8.5), (8.5, 11), (8.27, 11.69),
         (8.25, 11)]

# 60% royalty threshold per currency (KDP, from June 2025: 50% below it)
THRESHOLD_60 = {"USD": 9.99, "CAD": 13.99, "AUD": 13.99, "GBP": 7.99, "EUR": 9.99, "JPY": 1000,
                "PLN": 40.00, "SEK": 110.00}

# store -> currency, conversion KDP applied to a $9.99 list price on the real Rights & Pricing screen
STORES = [("Amazon.com", "USD", 1.0), ("Amazon.ca", "CAD", 14.26 / 9.99), ("Amazon.co.jp", "JPY", 1595 / 9.99),
          ("Amazon.co.uk", "GBP", 7.56 / 9.99), ("Amazon.com.au", "AUD", 14.75 / 9.99),
          ("Amazon.com.be", "EUR", 9.06 / 9.99), ("Amazon.de", "EUR", 9.06 / 9.99),
          ("Amazon.es", "EUR", 9.06 / 9.99), ("Amazon.fr", "EUR", 9.06 / 9.99), ("Amazon.ie", "EUR", 9.06 / 9.99),
          ("Amazon.it", "EUR", 9.06 / 9.99), ("Amazon.nl", "EUR", 9.06 / 9.99),
          ("Amazon.pl", "PLN", 38.94 / 9.99), ("Amazon.se", "SEK", 100.69 / 9.99)]

# Printing cost per store relative to the US cost (from the same screen: US $2.84 for 58 pages, large trim, B&W)
PRINT_RATIO = {"USD": 1.0, "CAD": 3.53 / 2.84, "JPY": 550 / 2.84, "GBP": 2.15 / 2.84, "AUD": 5.28 / 2.84,
               "EUR": 2.48 / 2.84, "PLN": 11.61 / 2.84, "SEK": 27.67 / 2.84}


def nearest_trim(page_w_in, page_h_in):
    """Return (trim_w, trim_h, has_bleed) for a PDF page size, or None if it matches no KDP trim."""
    for tw, th in TRIMS:
        if abs(page_w_in - tw) < 0.03 and abs(page_h_in - th) < 0.03:
            return tw, th, False
        if abs(page_w_in - (tw + BLEED_IN)) < 0.03 and abs(page_h_in - (th + 2 * BLEED_IN)) < 0.03:
            return tw, th, True
    return None


def is_large_trim(tw, th):
    return tw > 6.12 or th > 9


def spine_in(pages, paper="white"):
    return pages * SPINE_PER_PAGE.get(paper, SPINE_PER_PAGE["white"])


def cover_size(tw, th, pages, paper="white"):
    sp = spine_in(pages, paper)
    return 2 * tw + sp + 2 * BLEED_IN, th + 2 * BLEED_IN, sp


def printing_cost_usd(pages, large):
    """KDP black & white paperback printing cost on Amazon.com (estimate)."""
    if pages <= 108:
        return 2.84 if large else 2.30
    return round(1.00 + (0.017 if large else 0.012) * pages, 2)


def royalty(price, printing, currency="USD"):
    rate = 0.6 if price >= THRESHOLD_60.get(currency, 9.99) else 0.5
    return round(rate * price - printing, 2), rate


def recommend_us_price(pages, large, min_royalty=2.50):
    """Lowest '.99' price that reaches the 60% tier and leaves at least min_royalty."""
    printing = printing_cost_usd(pages, large)
    price = 9.99
    while royalty(price, printing)[0] < min_royalty and price < 99:
        price += 1.0
    return round(price, 2), printing


def _round_price(v, cur):
    if cur == "JPY":
        return str(int(math.ceil(v)))
    return f"{v:.2f}"


def marketplace_prices(us_price, pages, large):
    """Per-store rows: what to type (or keep) so every store earns the 60% rate."""
    us_print = printing_cost_usd(pages, large)
    rows = []
    for store, cur, rate in STORES:
        converted = us_price * rate
        th = THRESHOLD_60[cur]
        printing = round(us_print * PRINT_RATIO[cur], 2)
        if cur == "USD":
            price, action = us_price, "type"
        elif converted >= th:
            price, action = converted, "keep"
        else:
            price, action = th, "type"
        rows.append({"store": store, "currency": cur, "price": _round_price(price, cur), "printing": printing,
                     "threshold_60": th, "action": action,
                     "royalty_60": round(0.6 * float(_round_price(price, cur)) - printing, 2),
                     "estimate": not (pages <= 108 and large)})
    return rows
