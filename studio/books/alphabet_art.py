"""The 26 original A-Z vector drawings (drawn in a 200 x 200 box)."""
import math

from .design import (INK, circ, cloud_path, drop, ell, fp, heart, normal, poly, polyline, rect, shine, solid,
                     star, thin, tube, tube_line)


# --------------------------------------------------------------------------
# A - Z pictures (original artwork)
# --------------------------------------------------------------------------
def d_apple(c, F):
    ell(c, F, 25, 6, 175, 34, "#BFE3B4")
    p = c.beginPath()
    p.moveTo(100, 150)
    p.curveTo(130, 178, 186, 160, 180, 98)
    p.curveTo(176, 48, 140, 18, 118, 24)
    p.curveTo(108, 28, 92, 28, 82, 24)
    p.curveTo(60, 18, 24, 48, 20, 98)
    p.curveTo(14, 160, 70, 178, 100, 150)
    p.close()
    fp(c, F, p, "#E8453C")
    p = c.beginPath()
    p.moveTo(96, 148)
    p.curveTo(98, 165, 101, 180, 106, 194)
    p.lineTo(115, 191)
    p.curveTo(109, 177, 106, 162, 106, 146)
    p.close()
    fp(c, F, p, "#8B5A2B")
    p = c.beginPath()
    p.moveTo(108, 170)
    p.curveTo(125, 198, 160, 196, 180, 186)
    p.curveTo(160, 164, 128, 156, 108, 170)
    p.close()
    fp(c, F, p, "#4CAF50")
    thin(c, F)
    c.bezier(112, 171, 130, 177, 150, 181, 172, 184)
    c.arc(40, 60, 120, 140, 120, 50)
    normal(c, F)


def d_ball(c, F):
    ell(c, F, 35, 4, 165, 26, "#BFE3B4")
    circ(c, F, 100, 105, 85, "#E8453C")
    p = c.beginPath()
    p.moveTo(100, 190)
    p.curveTo(50, 160, 50, 50, 100, 20)
    p.curveTo(150, 50, 150, 160, 100, 190)
    p.close()
    fp(c, F, p, "#FFD166")
    p = c.beginPath()
    p.moveTo(100, 190)
    p.curveTo(80, 150, 80, 60, 100, 20)
    p.curveTo(120, 60, 120, 150, 100, 190)
    p.close()
    fp(c, F, p, "#4D96FF")
    thin(c, F)
    c.arc(30, 35, 170, 175, 130, 35)
    normal(c, F)


def d_cat(c, F):
    poly(c, F, [(38, 115), (45, 190), (92, 150)], "#F4A940")
    poly(c, F, [(162, 115), (155, 190), (108, 150)], "#F4A940")
    poly(c, F, [(52, 138), (54, 174), (80, 152)], "#F7B6C2")
    poly(c, F, [(148, 138), (146, 174), (120, 152)], "#F7B6C2")
    ell(c, F, 25, 25, 175, 160, "#F4A940")
    for x in (70, 130):
        ell(c, F, x - 16, 88, x + 16, 126, "#FFFFFF")
        c.setFillColor(INK)
        c.ellipse(x - 7, 92, x + 7, 118, stroke=0, fill=1)
        shine(c, x + 2, 111, 3)
    poly(c, F, [(91, 82), (109, 82), (100, 71)], "#F7B6C2")
    c.bezier(100, 71, 100, 58, 88, 55, 83, 64)
    c.bezier(100, 71, 100, 58, 112, 55, 117, 64)
    thin(c, F)
    for (y1, y2) in ((76, 84), (70, 68), (64, 52)):
        c.line(72, y1, 18, y2)
        c.line(128, y1, 182, y2)
    c.line(100, 158, 100, 140)
    c.line(87, 156, 90, 142)
    c.line(113, 156, 110, 142)
    normal(c, F)
    ell(c, F, 40, 66, 58, 78, "#F7B6C2")
    ell(c, F, 142, 66, 160, 78, "#F7B6C2")


def d_drum(c, F):
    ell(c, F, 20, 6, 180, 30, "#BFE3B4")
    p = c.beginPath()
    p.moveTo(30, 150)
    p.lineTo(30, 50)
    p.curveTo(30, 18, 170, 18, 170, 50)
    p.lineTo(170, 150)
    p.close()
    fp(c, F, p, "#E8453C")
    c.bezier(30, 64, 30, 34, 170, 34, 170, 64)
    polyline(c, [(30, 132), (53, 70), (76, 132), (100, 66), (124, 132), (147, 70), (170, 132)])
    ell(c, F, 30, 130, 170, 170, "#FFF3D6")
    tube_line(c, F, 18, 192, 80, 160, 7, "#C68B59")
    tube_line(c, F, 182, 192, 120, 160, 7, "#C68B59")
    circ(c, F, 80, 160, 8, "#FFFFFF")
    circ(c, F, 120, 160, 8, "#FFFFFF")


def egg_path(c):
    p = c.beginPath()
    p.moveTo(100, 190)
    p.curveTo(140, 190, 160, 130, 160, 80)
    p.curveTo(160, 40, 135, 15, 100, 15)
    p.curveTo(65, 15, 40, 40, 40, 80)
    p.curveTo(40, 130, 60, 190, 100, 190)
    p.close()
    return p


def d_egg(c, F):
    ell(c, F, 30, 4, 170, 28, "#BFE3B4")
    fp(c, F, egg_path(c), "#FFF3B0")
    c.saveState()
    c.clipPath(egg_path(c), stroke=0, fill=0)
    p = c.beginPath()
    xs = list(range(30, 176, 16))
    p.moveTo(30, 120)
    for i, x in enumerate(xs):
        p.lineTo(x, 132 if i % 2 else 118)
    p.lineTo(175, 90)
    for i, x in enumerate(reversed(xs)):
        p.lineTo(x, 80 if i % 2 else 94)
    p.close()
    fp(c, F, p, "#7EC8E3")
    for x in (70, 100, 130):
        circ(c, F, x, 152, 7, "#F7B6C2")
    for x in (62, 88, 114, 140):
        circ(c, F, x, 55, 6, "#C77DFF")
    c.restoreState()
    c.drawPath(egg_path(c), stroke=1, fill=0)


def d_fish(c, F):
    poly(c, F, [(140, 100), (190, 148), (175, 100), (190, 52)], "#FFBF69")
    p = c.beginPath()
    p.moveTo(60, 138)
    p.curveTo(78, 178, 118, 172, 126, 132)
    p.close()
    fp(c, F, p, "#FFBF69")
    p = c.beginPath()
    p.moveTo(80, 62)
    p.curveTo(84, 36, 106, 36, 112, 64)
    p.close()
    fp(c, F, p, "#FFBF69")
    p = c.beginPath()
    p.moveTo(20, 100)
    p.curveTo(50, 165, 130, 160, 152, 100)
    p.curveTo(130, 40, 50, 35, 20, 100)
    p.close()
    fp(c, F, p, "#FF9F1C")
    circ(c, F, 50, 112, 11, "#FFFFFF")
    solid(c, 52, 112, 5.5)
    shine(c, 54, 115, 2)
    c.bezier(78, 132, 92, 116, 92, 86, 78, 70)
    thin(c, F)
    for (x, y) in ((106, 116), (106, 88), (124, 102), (90, 102), (124, 128), (124, 76)):
        c.arc(x - 9, y - 9, x + 9, y + 9, -70, 140)
    c.bezier(22, 97, 27, 91, 31, 91, 36, 94)
    normal(c, F)
    circ(c, F, 22, 138, 7, "#BDE0FE")
    circ(c, F, 14, 160, 5, "#BDE0FE")
    circ(c, F, 26, 180, 8, "#BDE0FE")


def d_gift(c, F):
    rect(c, F, 35, 20, 130, 110, "#7B61FF")
    thin(c, F)
    for (x, y) in ((55, 45), (140, 50), (60, 100), (140, 105), (50, 75), (148, 78)):
        circ(c, F, x, y, 5, "#FFD166")
    normal(c, F)
    rect(c, F, 90, 20, 20, 110, "#FFD166")
    rect(c, F, 25, 128, 150, 30, "#9D8CFF")
    rect(c, F, 90, 128, 20, 30, "#FFD166")
    for sx in (-1, 1):
        p = c.beginPath()
        p.moveTo(100, 158)
        p.curveTo(100 + sx * 40, 200, 100 + sx * 70, 178, 100, 158)
        p.close()
        fp(c, F, p, "#FF6B6B")
    ell(c, F, 89, 150, 111, 168, "#FF6B6B")


def d_house(c, F):
    ell(c, F, 8, 6, 192, 30, "#BFE3B4")
    rect(c, F, 125, 140, 20, 44, "#C0C0C0")
    circ(c, F, 146, 192, 5, "#FFFFFF")
    circ(c, F, 158, 197, 4, "#FFFFFF")
    rect(c, F, 38, 20, 124, 100, "#FFE5B4")
    poly(c, F, [(20, 118), (100, 190), (180, 118)], "#E8453C")
    circ(c, F, 100, 146, 11, "#7EC8E3")
    rect(c, F, 85, 20, 30, 56, "#A0522D", r=8)
    solid(c, 108, 48, 3)
    for x in (50, 124):
        rect(c, F, x, 66, 26, 26, "#7EC8E3")
        c.line(x + 13, 66, x + 13, 92)
        c.line(x, 79, x + 26, 79)
    for x in (24, 172):
        p = c.beginPath()
        p.moveTo(x - 8, 20)
        p.curveTo(x - 12, 50, x + 12, 50, x + 8, 20)
        p.close()
        fp(c, F, p, "#4CAF50")


def d_icecream(c, F):
    cone = [(55, 112), (100, 8), (145, 112)]
    poly(c, F, cone, "#E9B872")
    c.saveState()
    p = c.beginPath()
    p.moveTo(*cone[0])
    p.lineTo(*cone[1])
    p.lineTo(*cone[2])
    p.close()
    c.clipPath(p, stroke=0, fill=0)
    thin(c, F)
    for k in range(-6, 8):
        x = 40 + k * 16
        c.line(x, 0, x + 110, 110)
        c.line(x + 110, 0, x, 110)
    c.restoreState()
    p = c.beginPath()
    p.moveTo(48, 110)
    p.curveTo(40, 168, 160, 168, 152, 110)
    p.curveTo(145, 92, 125, 92, 118, 108)
    p.curveTo(110, 96, 92, 96, 84, 108)
    p.curveTo(76, 92, 55, 92, 48, 110)
    p.close()
    fp(c, F, p, "#FF8FAB")
    p = c.beginPath()
    p.moveTo(62, 150)
    p.curveTo(55, 198, 145, 198, 138, 150)
    p.curveTo(120, 138, 80, 138, 62, 150)
    p.close()
    fp(c, F, p, "#A0E7E5")
    thin(c, F)
    for (x, y, dx, dy) in ((80, 165, 6, 4), (100, 178, -5, 5), (118, 163, 6, -3), (92, 155, 6, 2), (125, 175, -4, 4)):
        c.line(x, y, x + dx, y + dy)
    normal(c, F)
    c.bezier(100, 190, 102, 198, 108, 202, 114, 204)
    circ(c, F, 100, 188, 9, "#E8453C")


def d_jellyfish(c, F):
    for x in (58, 84, 112, 140):
        def b(p, x=x):
            p.moveTo(x, 110)
            p.curveTo(x - 22, 80, x + 22, 50, x, 14)
        tube(c, F, b, 7, "#E0AAFF")
    p = c.beginPath()
    p.moveTo(35, 105)
    p.curveTo(30, 196, 170, 196, 165, 105)
    pts = [165, 132.5, 100, 67.5, 35]
    for a, b2 in zip(pts, pts[1:]):
        p.curveTo(a - 8, 90, b2 + 8, 90, b2, 105)
    p.close()
    fp(c, F, p, "#C77DFF")
    solid(c, 78, 140, 6)
    solid(c, 122, 140, 6)
    shine(c, 80, 143, 2)
    shine(c, 124, 143, 2)
    c.bezier(88, 125, 94, 116, 106, 116, 112, 125)
    ell(c, F, 58, 122, 72, 130, "#F7B6C2")
    ell(c, F, 128, 122, 142, 130, "#F7B6C2")
    thin(c, F)
    for (x, y, r) in ((70, 168, 6), (100, 175, 5), (130, 166, 7), (55, 150, 4)):
        circ(c, F, x, y, r, "#E0AAFF")
    normal(c, F)


def d_kite(c, F):
    c.bezier(100, 45, 75, 25, 130, 18, 105, 0)
    for (x, y) in ((92, 34), (114, 12)):
        poly(c, F, [(x, y), (x - 11, y + 7), (x - 11, y - 7)], "#FF6B6B")
        poly(c, F, [(x, y), (x + 11, y + 7), (x + 11, y - 7)], "#FF6B6B")
    t, r, b, l, m = (100, 196), (160, 125), (100, 45), (40, 125), (100, 125)
    poly(c, F, [t, l, m], "#E8453C")
    poly(c, F, [t, r, m], "#FFD166")
    poly(c, F, [b, l, m], "#4D96FF")
    poly(c, F, [b, r, m], "#4CAF50")
    thin(c, F)
    c.bezier(160, 125, 175, 100, 168, 80, 190, 60)
    normal(c, F)


def d_leaf(c, F):
    tube_line(c, F, 100, 40, 100, 6, 7, "#8B5A2B")
    p = c.beginPath()
    p.moveTo(100, 34)
    p.curveTo(25, 60, 40, 165, 100, 196)
    p.curveTo(160, 165, 175, 60, 100, 34)
    p.close()
    fp(c, F, p, "#7CC36E")
    c.line(100, 36, 100, 186)
    thin(c, F)
    for (y, w) in ((62, 36), (92, 46), (122, 44), (152, 32)):
        c.bezier(100, y, 100 - w * 0.4, y + 6, 100 - w * 0.8, y + 14, 100 - w, y + 24)
        c.bezier(100, y, 100 + w * 0.4, y + 6, 100 + w * 0.8, y + 14, 100 + w, y + 24)
    normal(c, F)
    drop(c, F, 150, 60, 7, "#BDE0FE")


def d_moon(c, F):
    c.saveState()
    p = c.beginPath()
    p.circle(90, 100, 80 + F.lw)
    c.clipPath(p, stroke=0, fill=0)
    circ(c, F, 90, 100, 80, "#FFD166")
    c.setFillColor(F.bg)
    c.circle(125, 125, 65, stroke=1, fill=1)
    c.restoreState()
    c.bezier(42, 116, 48, 106, 58, 106, 64, 116)
    c.bezier(42, 86, 50, 74, 62, 74, 70, 84)
    ell(c, F, 30, 96, 44, 104, "#F7B6C2")
    star(c, F, 158, 178, 13, "#FFD166")
    star(c, F, 186, 74, 10, "#FFD166")
    star(c, F, 168, 26, 12, "#FFD166")
    star(c, F, 22, 186, 9, "#FFD166")


def d_nest(c, F):
    ell(c, F, 48, 70, 90, 128, "#BDE0FE")
    ell(c, F, 82, 76, 122, 138, "#FFFFFF")
    ell(c, F, 115, 70, 155, 126, "#BDE0FE")
    nest = c.beginPath()
    nest.moveTo(14, 100)
    nest.curveTo(20, 28, 180, 28, 186, 100)
    nest.curveTo(150, 84, 50, 84, 14, 100)
    nest.close()
    fp(c, F, nest, "#C68B59")
    c.saveState()
    clip = c.beginPath()
    clip.moveTo(14, 100)
    clip.curveTo(20, 28, 180, 28, 186, 100)
    clip.curveTo(150, 84, 50, 84, 14, 100)
    clip.close()
    c.clipPath(clip, stroke=0, fill=0)
    thin(c, F)
    for (a, b2, d) in ((20, 82, 0), (40, 72, 30), (30, 62, -20), (60, 55, 10), (80, 82, -10), (110, 66, 20)):
        c.bezier(a, b2, a + 40, b2 - 12 + d * 0.2, a + 80, b2 + 8, a + 130, b2 - 10)
        c.bezier(a + 140, b2 + 4, a + 90, b2 - 10, a + 50, b2 + 6, a, b2 - 14)
    c.restoreState()
    c.drawPath(clip, stroke=1, fill=0)
    p = c.beginPath()
    p.moveTo(160, 92)
    p.curveTo(175, 112, 192, 112, 196, 104)
    p.curveTo(188, 92, 172, 88, 160, 92)
    p.close()
    fp(c, F, p, "#4CAF50")


def d_owl(c, F):
    tube_line(c, F, 6, 30, 194, 30, 12, "#8B5A2B")
    p = c.beginPath()
    p.moveTo(170, 36)
    p.curveTo(178, 52, 192, 54, 196, 46)
    p.curveTo(190, 36, 178, 32, 170, 36)
    p.close()
    fp(c, F, p, "#4CAF50")
    poly(c, F, [(48, 150), (52, 196), (82, 166)], "#9D6B7A")
    poly(c, F, [(152, 150), (148, 196), (118, 166)], "#9D6B7A")
    ell(c, F, 40, 34, 160, 176, "#B5838D")
    ell(c, F, 68, 40, 132, 112, "#FFE5D9")
    thin(c, F)
    for (x, y) in ((88, 96), (112, 96), (100, 80), (82, 66), (118, 66), (100, 52)):
        c.arc(x - 7, y - 7, x + 7, y + 7, 200, 140)
    normal(c, F)
    for sx in (-1, 1):
        p = c.beginPath()
        x0 = 100 + sx * 55
        p.moveTo(x0, 130)
        p.curveTo(100 + sx * 82, 100, 100 + sx * 66, 62, 100 + sx * 40, 50)
        p.curveTo(100 + sx * 46, 80, 100 + sx * 46, 110, x0, 130)
        p.close()
        fp(c, F, p, "#9D6B7A")
    for x in (76, 124):
        circ(c, F, x, 136, 24, "#FFD166")
        circ(c, F, x, 136, 15, "#FFFFFF")
        solid(c, x, 136, 9)
        shine(c, x + 3, 140, 3)
    poly(c, F, [(91, 116), (109, 116), (100, 98)], "#FF9F1C")
    for x0 in (80, 120):
        for dx in (-8, 0, 8):
            circ(c, F, x0 + dx, 36, 4.5, "#FF9F1C")


def d_pencil(c, F):
    c.saveState()
    c.translate(100, 100)
    c.rotate(35)
    c.translate(-100, -100)
    rect(c, F, 10, 83, 26, 34, "#FF8FAB", r=8)
    rect(c, F, 30, 83, 18, 34, "#C0C0C0")
    c.line(36, 83, 36, 117)
    c.line(42, 83, 42, 117)
    rect(c, F, 48, 83, 100, 34, "#FFD166")
    c.line(48, 94.3, 148, 94.3)
    c.line(48, 105.7, 148, 105.7)
    poly(c, F, [(148, 83), (186, 100), (148, 117)], "#F2D0A4")
    c.setFillColor(INK)
    p = c.beginPath()
    p.moveTo(173, 94.2)
    p.lineTo(186, 100)
    p.lineTo(173, 105.8)
    p.close()
    c.drawPath(p, stroke=1, fill=1)
    c.restoreState()
    thin(c, F)
    c.bezier(30, 30, 60, 10, 90, 50, 120, 25)
    c.bezier(120, 25, 140, 10, 160, 30, 180, 20)
    normal(c, F)


def d_quilt(c, F):
    rect(c, F, 12, 12, 176, 176, "#FFFFFF", r=10)
    cols = ["#FF8FAB", "#7EC8E3", "#FFD166", "#B7E4A7"]
    for i in range(4):
        for j in range(4):
            x, y = 20 + i * 40, 20 + j * 40
            if (i + j) % 2 == 0:
                poly(c, F, [(x, y), (x + 40, y), (x, y + 40)], cols[(i + j) % 4])
                poly(c, F, [(x + 40, y), (x + 40, y + 40), (x, y + 40)], cols[(i + j + 1) % 4])
            else:
                rect(c, F, x, y, 40, 40, "#FFF3D6")
                if (i * 3 + j) % 2:
                    heart(c, F, x + 20, y + 19, 11, "#E8453C")
                else:
                    star(c, F, x + 20, y + 20, 13, "#C77DFF")
    c.saveState()
    thin(c, F, 0.5)
    c.setDash(4, 4)
    c.roundRect(16, 16, 168, 168, 8, stroke=1, fill=0)
    c.restoreState()


def d_rocket(c, F):
    p = c.beginPath()
    p.moveTo(78, 56)
    p.curveTo(72, 28, 94, 22, 100, 0)
    p.curveTo(106, 22, 128, 28, 122, 56)
    p.close()
    fp(c, F, p, "#FF9F1C")
    p = c.beginPath()
    p.moveTo(88, 56)
    p.curveTo(86, 40, 98, 34, 100, 18)
    p.curveTo(102, 34, 114, 40, 112, 56)
    p.close()
    fp(c, F, p, "#FFD166")
    poly(c, F, [(72, 100), (38, 52), (40, 40), (74, 56)], "#E8453C")
    poly(c, F, [(128, 100), (162, 52), (160, 40), (126, 56)], "#E8453C")

    def body():
        p = c.beginPath()
        p.moveTo(70, 50)
        p.lineTo(70, 130)
        p.curveTo(70, 165, 90, 185, 100, 198)
        p.curveTo(110, 185, 130, 165, 130, 130)
        p.lineTo(130, 50)
        p.close()
        return p
    fp(c, F, body(), "#DDE6F0")
    c.saveState()
    c.clipPath(body(), stroke=0, fill=0)
    rect(c, F, 60, 155, 80, 60, "#E8453C")
    rect(c, F, 60, 40, 80, 22, "#4D96FF")
    c.restoreState()
    c.drawPath(body(), stroke=1, fill=0)
    circ(c, F, 100, 118, 18, "#FFFFFF")
    circ(c, F, 100, 118, 12, "#7EC8E3")
    shine(c, 96, 122, 3)
    tube_line(c, F, 100, 62, 100, 90, 6, "#E8453C")
    for (x, y, r) in ((25, 170, 8), (175, 150, 10), (30, 110, 6), (170, 190, 6)):
        star(c, F, x, y, r, "#FFD166")


def d_sun(c, F):
    for i in range(12):
        a = i * math.pi / 6
        da = math.radians(10)
        poly(c, F, [(100 + 58 * math.cos(a - da), 100 + 58 * math.sin(a - da)),
                    (100 + 94 * math.cos(a), 100 + 94 * math.sin(a)),
                    (100 + 58 * math.cos(a + da), 100 + 58 * math.sin(a + da))], "#FF9F1C")
    circ(c, F, 100, 100, 62, "#FFD166")
    solid(c, 80, 112, 7)
    solid(c, 120, 112, 7)
    shine(c, 82, 115, 2.5)
    shine(c, 122, 115, 2.5)
    p = c.beginPath()
    p.moveTo(74, 86)
    p.curveTo(84, 60, 116, 60, 126, 86)
    p.curveTo(108, 80, 92, 80, 74, 86)
    p.close()
    fp(c, F, p, "#FF6B6B")
    ell(c, F, 58, 84, 74, 94, "#F7B6C2")
    ell(c, F, 126, 84, 142, 94, "#F7B6C2")


def d_tree(c, F):
    ell(c, F, 20, 4, 180, 28, "#BFE3B4")
    p = c.beginPath()
    p.moveTo(76, 14)
    p.curveTo(90, 24, 88, 60, 90, 110)
    p.lineTo(110, 110)
    p.curveTo(112, 60, 110, 24, 124, 14)
    p.close()
    fp(c, F, p, "#8B5A2B")
    c.setFillColor(INK)
    c.ellipse(94, 40, 106, 56, stroke=0, fill=1)
    fp(c, F, cloud_path(c, 100, 132, 72, 48, n=11, bulge=1.28, off=0.2), "#4CAF50")
    for (x, y) in ((62, 140), (100, 120), (138, 145), (80, 165), (122, 172), (150, 115), (55, 108)):
        circ(c, F, x, y, 7, "#E8453C")
    thin(c, F)
    c.bezier(45, 150, 50, 160, 58, 168, 66, 172)
    normal(c, F)


def d_umbrella(c, F):
    def handle(p):
        p.moveTo(100, 150)
        p.lineTo(100, 40)
        p.curveTo(100, 14, 70, 14, 70, 36)
    tube(c, F, handle, 9, "#8B5A2B")
    p = c.beginPath()
    p.moveTo(15, 110)
    p.curveTo(18, 196, 182, 196, 185, 110)
    pts = [185, 142.5, 100, 57.5, 15]
    for a, b2 in zip(pts, pts[1:]):
        p.curveTo(a - 8, 128, b2 + 8, 128, b2, 110)
    p.close()
    fp(c, F, p, "#E8453C")
    for x in (57.5, 100, 142.5):
        c.bezier(100, 174, (100 + x) / 2 + (x - 100) * 0.3, 160, x, 130, x, 110)
    tube_line(c, F, 100, 174, 100, 190, 5, "#8B5A2B")
    for (x, y) in ((25, 170), (178, 168), (30, 60), (168, 70), (150, 25)):
        drop(c, F, x, y, 7, "#BDE0FE")


def d_van(c, F):
    c.line(4, 16, 196, 16)
    p = c.beginPath()
    p.moveTo(15, 40)
    p.lineTo(15, 140)
    p.curveTo(15, 155, 25, 160, 40, 160)
    p.lineTo(140, 160)
    p.curveTo(155, 160, 160, 150, 165, 135)
    p.lineTo(180, 95)
    p.curveTo(185, 85, 185, 75, 185, 60)
    p.lineTo(185, 40)
    p.close()
    fp(c, F, p, "#4D96FF")
    poly(c, F, [(130, 145), (152, 145), (167, 100), (130, 100)], "#CDEFFF")
    rect(c, F, 28, 102, 40, 42, "#CDEFFF", r=6)
    rect(c, F, 78, 102, 40, 42, "#CDEFFF", r=6)
    c.line(125, 44, 125, 100)
    rect(c, F, 110, 80, 10, 5, "#C0C0C0", r=2)
    rect(c, F, 15, 64, 170, 12, "#FFD166")
    ell(c, F, 170, 80, 184, 92, "#FFF3B0")
    rect(c, F, 8, 34, 184, 12, "#C0C0C0", r=5)
    for x in (55, 145):
        circ(c, F, x, 40, 22, "#555555")
        circ(c, F, x, 40, 9, "#DDDDDD")


def d_watermelon(c, F):
    def half(r):
        p = c.beginPath()
        p.moveTo(100 - r, 125)
        p.arcTo(100 - r, 125 - r, 100 + r, 125 + r, 180, 180)
        p.close()
        return p
    fp(c, F, half(88), "#2E8B57")
    fp(c, F, half(78), "#B7E4A7")
    fp(c, F, half(68), "#FF6B6B")
    c.setFillColor(INK)
    for (x, y, a) in ((60, 105, 20), (82, 85, 5), (118, 85, -5), (140, 105, -20), (100, 108, 0), (72, 118, 10), (128, 118, -10), (100, 75, 0)):
        c.saveState()
        c.translate(x, y)
        c.rotate(a)
        c.ellipse(-3.5, -6, 3.5, 6, stroke=0, fill=1)
        c.restoreState()
    for (x, y) in ((30, 170), (170, 168), (100, 175)):
        star(c, F, x, y, 9, "#FFD166")


def d_xylophone(c, F):
    tube_line(c, F, 18, 150, 182, 114, 8, "#8B5A2B")
    tube_line(c, F, 18, 50, 182, 86, 8, "#8B5A2B")
    cols = ["#E8453C", "#FF9F1C", "#FFD166", "#4CAF50", "#4D96FF", "#7B61FF", "#C77DFF"]
    for i in range(7):
        x = 26 + i * 21
        top, bot = 168 - i * 7, 34 + i * 7
        rect(c, F, x, bot, 17, top - bot, cols[i], r=5)
        cx = x + 8.5
        ty = 150 - 36 * (cx - 18) / 164
        by = 50 + 36 * (cx - 18) / 164
        solid(c, cx, ty, 2.5)
        solid(c, cx, by, 2.5)
    tube_line(c, F, 30, 8, 122, 24, 5, "#C68B59")
    circ(c, F, 128, 25, 9, "#E8453C")
    tube_line(c, F, 70, 24, 150, 6, 5, "#C68B59")
    circ(c, F, 156, 5, 9, "#4D96FF")


def d_yoyo(c, F):
    circ(c, F, 100, 85, 70, "#E8453C")
    circ(c, F, 100, 85, 52, "#FF8FAB")
    thin(c, F)
    for i in range(8):
        a = i * math.pi / 4
        c.line(100 + 20 * math.cos(a), 85 + 20 * math.sin(a), 100 + 50 * math.cos(a), 85 + 50 * math.sin(a))
    normal(c, F)
    circ(c, F, 100, 85, 16, "#FFFFFF")
    c.bezier(100, 85, 92, 130, 112, 160, 100, 182)
    c.circle(100, 190, 8, stroke=1, fill=0)
    thin(c, F)
    c.arc(8, 40, 48, 130, 120, 120)
    c.arc(152, 40, 192, 130, -60, 120)
    normal(c, F)
    star(c, F, 165, 175, 10, "#FFD166")
    star(c, F, 35, 170, 8, "#FFD166")


def d_zebra(c, F):
    for sx in (-1, 1):
        p = c.beginPath()
        p.moveTo(100 + sx * 32, 150)
        p.curveTo(100 + sx * 58, 186, 100 + sx * 44, 202, 100 + sx * 22, 166)
        p.close()
        fp(c, F, p, "#FFFFFF")
    c.setFillColor(INK)
    p = c.beginPath()
    p.moveTo(76, 162)
    for (x, y) in ((80, 188), (90, 168), (100, 194), (110, 168), (120, 188), (124, 162)):
        p.lineTo(x, y)
    p.close()
    c.drawPath(p, stroke=1, fill=1)

    def head():
        p = c.beginPath()
        p.moveTo(100, 176)
        p.curveTo(150, 176, 150, 110, 140, 70)
        p.curveTo(135, 50, 65, 50, 60, 70)
        p.curveTo(50, 110, 50, 176, 100, 176)
        p.close()
        return p
    fp(c, F, head(), "#FFFFFF")
    c.saveState()
    c.clipPath(head(), stroke=0, fill=0)
    c.setFillColor(INK)
    for y in (152, 126, 100):
        for sx in (-1, 1):
            p = c.beginPath()
            p.moveTo(100 + sx * 60, y + 8)
            p.curveTo(100 + sx * 40, y + 10, 100 + sx * 26, y + 2, 100 + sx * 18, y - 4)
            p.curveTo(100 + sx * 28, y - 2, 100 + sx * 40, y - 2, 100 + sx * 60, y - 6)
            p.close()
            c.drawPath(p, stroke=0, fill=1)
    p = c.beginPath()
    p.moveTo(92, 180)
    p.curveTo(95, 165, 98, 156, 100, 146)
    p.curveTo(102, 156, 105, 165, 108, 180)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.restoreState()
    c.drawPath(head(), stroke=1, fill=0)
    for x in (80, 120):
        circ(c, F, x, 118, 10, "#FFFFFF")
        solid(c, x, 117, 5.5)
        shine(c, x + 2, 120, 2)
    ell(c, F, 62, 20, 138, 80, "#B0B0B0")
    c.setFillColor(INK)
    c.ellipse(78, 46, 88, 58, stroke=0, fill=1)
    c.ellipse(112, 46, 122, 58, stroke=0, fill=1)
    c.bezier(84, 34, 94, 27, 106, 27, 116, 34)


LETTERS = [
    ("A", "APPLE", d_apple), ("B", "BALL", d_ball), ("C", "CAT", d_cat),
    ("D", "DRUM", d_drum), ("E", "EGG", d_egg), ("F", "FISH", d_fish),
    ("G", "GIFT", d_gift), ("H", "HOUSE", d_house), ("I", "ICE CREAM", d_icecream),
    ("J", "JELLYFISH", d_jellyfish), ("K", "KITE", d_kite), ("L", "LEAF", d_leaf),
    ("M", "MOON", d_moon), ("N", "NEST", d_nest), ("O", "OWL", d_owl),
    ("P", "PENCIL", d_pencil), ("Q", "QUILT", d_quilt), ("R", "ROCKET", d_rocket),
    ("S", "SUN", d_sun), ("T", "TREE", d_tree), ("U", "UMBRELLA", d_umbrella),
    ("V", "VAN", d_van), ("W", "WATERMELON", d_watermelon), ("X", "XYLOPHONE", d_xylophone),
    ("Y", "YO-YO", d_yoyo), ("Z", "ZEBRA", d_zebra),
]
