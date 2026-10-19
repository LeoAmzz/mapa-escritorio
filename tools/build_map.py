#!/usr/bin/env python3
"""Gera o tileset em pixel art, o mapa .tmj (Tiled / WorkAdventure) e as prévias.

Uso:  python tools/build_map.py
Saída: tilesets/escritorio.png, escritorio.tmj, preview.png, preview_areas.png
"""
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
T = 32            # tamanho do tile (WorkAdventure usa 32x32)
W, H = 84, 64     # tamanho do mapa em tiles
ATLAS_COLS = 16

C = dict(
    grass=(92, 158, 64), grass_l=(116, 178, 78), grass_d=(76, 138, 56),
    dgrass=(68, 128, 52), dgrass_d=(58, 112, 46), dgrass_l=(80, 142, 60),
    water=(72, 130, 212), water_l=(108, 162, 232), water_d=(60, 112, 190), foam=(186, 218, 246),
    cliff=(124, 88, 58), cliff_l=(156, 116, 76), cliff_d=(90, 62, 42),
    stone=(62, 66, 78), stone_l=(78, 82, 96), stone_d=(48, 51, 61),
    wl=(178, 122, 78), wl_d=(148, 98, 60), wl_l=(192, 138, 92),
    wd=(124, 82, 58), wd_d=(100, 65, 46), wd_l=(138, 94, 66),
    tg=(170, 176, 184), tg_d=(144, 150, 160), tg_l=(188, 194, 200),
    sl=(80, 84, 94), sl_d=(64, 68, 78), sl_l=(92, 96, 106),
    navy=(30, 34, 52), navy_l=(46, 52, 76),
    face=(206, 210, 218), face_l=(232, 234, 240), face_d=(156, 162, 174), face_s=(118, 124, 136),
    brick=(124, 130, 142), brick_d=(104, 110, 122), brick_l=(142, 148, 160),
    white=(238, 239, 243), white_e=(192, 195, 204), white_f=(168, 172, 184),
    dark=(42, 46, 56), screen=(84, 164, 226), screen_l=(156, 210, 248),
    chair=(66, 70, 82), chair_d=(48, 52, 62),
    yellow=(238, 190, 60), yellow_d=(196, 146, 36),
    cw=(228, 228, 234), cw_d=(184, 184, 196),
    pot=(186, 106, 64), pot_d=(146, 80, 48), leaf=(64, 150, 72), leaf_l=(104, 188, 90), leaf_d=(42, 110, 54),
    wood=(134, 88, 54), wood_d=(100, 64, 40), wood_l=(162, 112, 72),
    trunk=(104, 72, 46), canopy=(52, 122, 58), canopy_l=(84, 158, 72), canopy_d=(36, 94, 46),
    shadow=(0, 0, 0, 55),
)


# --------------------------------------------------------------------------- desenho

def new(w=T, h=T):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def rect(d, x0, y0, x1, y1, c):
    d.rectangle([x0, y0, x1, y1], fill=c)


def lighten(c, k=24):
    return tuple(min(255, v + k) for v in c[:3])


def noise(im, colors, n, seed):
    rng = random.Random(seed)
    px = im.load()
    for _ in range(n):
        px[rng.randrange(im.width), rng.randrange(im.height)] = rng.choice(colors)


def grass(seed):
    im = new(); d = ImageDraw.Draw(im)
    rect(d, 0, 0, 31, 31, C["grass"])
    noise(im, [C["grass_l"], C["grass_d"]], 70, seed)
    rng = random.Random(seed + 99)
    for _ in range(6):  # tufos
        x, y = rng.randrange(2, 30), rng.randrange(3, 30)
        rect(d, x, y - 2, x, y, C["grass_d"]); rect(d, x + 1, y - 3, x + 1, y - 1, C["grass_l"])
    return im


def grass_flowers(seed):
    im = grass(seed); d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    for _ in range(4):
        x, y = rng.randrange(3, 28), rng.randrange(3, 28)
        col = rng.choice([(240, 240, 250), (250, 214, 80), (236, 110, 140)])
        rect(d, x, y, x + 1, y + 1, col)
    return im


def edged(base_fn, mask, edge_fn, land=None, rim=None, r=12):
    """Aplica borda nos lados indicados pela máscara (N=1, L=2, S=4, O=8).
    Onde dois lados vizinhos têm borda, arredonda o canto pintando `land` por fora do raio."""
    im = base_fn(); px = im.load()
    corners = [(1 | 8, 0, 0), (1 | 2, 31, 0), (4 | 2, 31, 31), (4 | 8, 0, 31)]
    for y in range(T):
        for x in range(T):
            dists = []
            if mask & 1: dists.append(y)
            if mask & 2: dists.append(31 - x)
            if mask & 4: dists.append(31 - y)
            if mask & 8: dists.append(x)
            if dists:
                c = edge_fn(min(dists), x, y)
                if c: px[x, y] = c
            if land:
                for bits, cx, cy in corners:
                    if mask & bits == bits and abs(x - cx) < r and abs(y - cy) < r:
                        ox, oy = cx + (r if cx == 0 else -r), cy + (r if cy == 0 else -r)
                        dist = math.hypot(x - ox, y - oy)
                        if dist > r:
                            px[x, y] = land[(x * 7 + y * 3) % len(land)]
                        elif rim and dist > r - 2:
                            px[x, y] = rim
    return im


def dark_grass(mask):
    def base():
        im = new(); d = ImageDraw.Draw(im)
        rect(d, 0, 0, 31, 31, C["dgrass"])
        noise(im, [C["dgrass_l"], C["dgrass_d"]], 60, 7 + mask)
        return im

    def edge(dist, x, y):
        if dist == 0 or (dist < 3 and (x + y) % 2 == 0) or (dist < 6 and (x * 3 + y) % 7 == 0):
            return C["grass"]
        return None
    return edged(base, mask, edge, land=[C["grass"]] * 6 + [C["grass_l"], C["grass_d"]])


def water(mask):
    def base():
        im = new(); d = ImageDraw.Draw(im)
        rect(d, 0, 0, 31, 31, C["water"])
        rng = random.Random(3 + mask)
        for _ in range(5):
            x, y = rng.randrange(0, 26), rng.randrange(2, 30)
            rect(d, x, y, x + rng.randrange(3, 6), y, C["water_l"])
        noise(im, [C["water_d"]], 25, mask)
        return im

    def edge(dist, x, y):
        return C["foam"] if dist < 2 else (C["water_l"] if dist < 3 else None)
    return edged(base, mask, edge, land=[C["grass"]] * 6 + [C["grass_l"], C["grass_d"]], rim=C["foam"])


def cliff():
    im = new(); d = ImageDraw.Draw(im)
    rect(d, 0, 0, 31, 31, C["cliff"])
    rng = random.Random(11)
    for _ in range(9):
        x, y = rng.randrange(0, 26), rng.randrange(0, 26)
        w, h = rng.randrange(4, 8), rng.randrange(3, 6)
        rect(d, x, y + h, x + w, y + h + 1, C["cliff_d"])
        rect(d, x, y, x + w, y + h - 1, C["cliff_l"])
    rect(d, 0, 0, 1, 31, C["cliff_d"])
    return im


def shade(c, k):
    return tuple(max(0, min(255, v + int(k))) for v in c[:3])


def vgrad(d, x0, y0, x1, y1, top, bottom):
    """Gradiente vertical em faixas de 1 px."""
    n = max(1, y1 - y0)
    for y in range(y0, y1 + 1):
        t = (y - y0) / n
        rect(d, x0, y, x1, y, tuple(round(a + (b - a) * t) for a, b in zip(top[:3], bottom[:3])))


OUTLINE = (34, 30, 42, 255)


def outline(im, color=OUTLINE):
    """Contorno de 1 px em volta das partes opacas (ignora a sombra semitransparente)."""
    src = im.load(); out = im.copy(); px = out.load()
    for y in range(im.height):
        for x in range(im.width):
            if src[x, y][3] == 255:
                continue
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < im.width and 0 <= ny < im.height and src[nx, ny][3] == 255:
                    px[x, y] = color
                    break
    return out


def pavers(base, dk, lt, size=16):
    im = new(); d = ImageDraw.Draw(im)
    rect(d, 0, 0, 31, 31, base)
    noise(im, [shade(base, 7), shade(base, -6)], 60, sum(base))
    for k in range(0, 32, size):
        rect(d, 0, k + size - 1, 31, k + size - 1, dk); rect(d, k + size - 1, 0, k + size - 1, 31, dk)
        rect(d, 0, k, 31, k, lt); rect(d, k, 0, k, 31, lt)
        rect(d, 0, k + size - 2, 31, k + size - 2, shade(base, -4))
    return im


def planks(base, dk, lt, seed):
    """Tábuas horizontais de 8 px. As pontas de cada fileira têm o tom base (emendam com o tile
    vizinho) e o trecho do meio varia de tom, o que quebra a repetição."""
    im = new(); d = ImageDraw.Draw(im)
    rng = random.Random(seed * 31 + 7)
    for row in range(4):
        y0 = row * 8
        j1 = (row * 11 + 3 + seed * 5) % 14 + 2
        j2 = j1 + 10 + (row + seed) % 6
        for a, b, k in ((0, j1 - 1, 0), (j1, j2 - 1, rng.randrange(-12, 12)), (j2, 31, 0)):
            if a > b:
                continue
            rect(d, a, y0, b, y0 + 6, shade(base, k))
            rect(d, a, y0, b, y0, shade(base, k + 12))
            rect(d, a, y0 + 6, b, y0 + 6, shade(base, k - 6))
            for _ in range(2):
                gx = rng.randrange(a, max(a + 1, b - 3)); gy = y0 + rng.randrange(2, 5)
                rect(d, gx, gy, min(b, gx + rng.randrange(3, 8)), gy, shade(base, k - 10))
        rect(d, 0, y0 + 7, 31, y0 + 7, dk)
        for j in (j1, j2):
            rect(d, j, y0, j, y0 + 6, dk)
            if j + 1 <= 31:
                rect(d, j + 1, y0 + 1, j + 1, y0 + 5, shade(base, 16))
    return im


def wall_top():
    im = new(); d = ImageDraw.Draw(im)
    rect(d, 0, 0, 31, 31, C["navy"])
    for y in range(0, 32, 4):
        for x in range((y // 4) % 2 * 2, 32, 4):
            im.putpixel((x, y), C["navy_l"])
    return im


def face(kind):
    im = new(); d = ImageDraw.Draw(im)
    vgrad(d, 0, 3, 31, 24, shade(C["face"], 12), shade(C["face"], -10))
    rect(d, 0, 0, 31, 0, (250, 250, 252)); rect(d, 0, 1, 31, 2, C["face_l"])
    rect(d, 0, 3, 31, 3, shade(C["face"], -22))
    rect(d, 31, 4, 31, 24, shade(C["face"], -14))                      # junta do painel
    rect(d, 0, 25, 31, 29, C["wood"]); rect(d, 0, 25, 31, 25, C["wood_l"])  # rodapé
    rect(d, 0, 29, 31, 29, C["wood_d"]); rect(d, 0, 30, 31, 31, (58, 48, 46))
    if kind == "green":      # quadro verde
        rect(d, 4, 5, 27, 22, (50, 56, 68)); rect(d, 4, 5, 27, 5, (90, 98, 112))
        vgrad(d, 6, 7, 25, 20, (92, 160, 108), (60, 122, 80))
        for i in range(4):
            im.putpixel((9 + i, 15 - i), (140, 200, 150))
        rect(d, 5, 22, 26, 23, (170, 176, 188))
    elif kind == "blue":     # janela
        rect(d, 3, 4, 28, 22, (150, 156, 168)); rect(d, 4, 5, 27, 21, (244, 246, 250))
        vgrad(d, 6, 7, 25, 19, (176, 214, 248), (96, 150, 222))
        rect(d, 15, 7, 16, 19, (244, 246, 250)); rect(d, 6, 13, 25, 13, (244, 246, 250))
        for i in range(5):
            im.putpixel((8 + i, 12 - i), (226, 240, 252)); im.putpixel((19 + i, 18 - i), (176, 210, 246))
        rect(d, 2, 22, 29, 23, (236, 238, 244)); rect(d, 2, 24, 29, 24, shade(C["face"], -30))
    elif kind == "board":    # quadro branco
        vgrad(d, 2, 4, 29, 22, (190, 196, 206), (130, 136, 148))
        rect(d, 3, 5, 28, 20, (250, 250, 253)); rect(d, 3, 5, 28, 5, (230, 232, 238))
        rect(d, 6, 8, 17, 8, (60, 110, 200)); rect(d, 6, 11, 22, 11, (210, 70, 70))
        rect(d, 6, 14, 14, 14, (60, 150, 90)); rect(d, 19, 14, 25, 18, (250, 220, 120))
        rect(d, 8, 21, 23, 22, (120, 126, 138)); rect(d, 10, 21, 12, 21, (210, 70, 70))
    elif kind == "tv":
        rect(d, 3, 4, 28, 21, C["dark"]); rect(d, 3, 4, 28, 4, (80, 86, 100))
        vgrad(d, 5, 6, 26, 19, (104, 186, 240), (52, 112, 200))
        rect(d, 7, 8, 16, 9, (230, 240, 252)); rect(d, 7, 12, 22, 12, (180, 214, 244)); rect(d, 7, 15, 19, 15, (180, 214, 244))
        rect(d, 13, 22, 18, 23, (70, 74, 86)); im.putpixel((26, 20), (90, 220, 120))
    elif kind == "art":
        rect(d, 7, 3, 24, 22, C["wood_d"]); rect(d, 8, 4, 23, 21, C["wood_l"])
        vgrad(d, 10, 6, 21, 14, (160, 206, 244), (210, 230, 250))
        rect(d, 10, 15, 21, 19, (90, 160, 80)); d.polygon([(10, 15), (14, 10), (18, 15)], fill=(70, 130, 70))
        rect(d, 17, 7, 19, 9, (250, 220, 90))
    return im


def ext_face(window):
    im = new(); d = ImageDraw.Draw(im)
    rect(d, 0, 0, 31, 31, C["brick"])
    for i, y in enumerate(range(5, 30, 6)):
        rect(d, 0, y, 31, y, C["brick_d"])
        for x in range(4 + (i % 2) * 6, 32, 12):
            rect(d, x, y - 5, x, y - 1, C["brick_d"])
    rect(d, 0, 0, 31, 1, C["brick_l"]); rect(d, 0, 29, 31, 31, (84, 90, 100))
    if window:
        rect(d, 9, 6, 22, 22, (236, 238, 244)); rect(d, 11, 8, 20, 20, (88, 140, 220))
        rect(d, 15, 8, 16, 20, (236, 238, 244)); rect(d, 12, 9, 13, 12, (150, 192, 240))
    return im


# ------------------------------------------------------------------- mobiliário

def shadow(d, box):
    d.ellipse(box, fill=C["shadow"])


def desk(variant):
    """Estação individual de 2 tiles: monitor à esquerda (a cadeira fica embaixo), objetos à direita."""
    im = new(64, 32); d = ImageDraw.Draw(im)
    shadow(d, [1, 23, 62, 31])
    rect(d, 4, 24, 6, 29, (120, 124, 136)); rect(d, 57, 24, 59, 29, (120, 124, 136))  # pernas
    d.rounded_rectangle([1, 18, 62, 26], 2, fill=C["white_f"])
    rect(d, 2, 25, 61, 25, shade(C["white_f"], -16))
    d.rounded_rectangle([1, 3, 62, 22], 3, fill=C["white"])
    vgrad(d, 3, 5, 60, 20, (248, 248, 251), (226, 228, 234))
    rect(d, 3, 4, 60, 4, (255, 255, 255)); rect(d, 2, 22, 61, 22, C["white_e"])
    # monitor
    d.ellipse([10, 13, 21, 17], fill=(150, 154, 166)); rect(d, 14, 11, 17, 14, (96, 100, 112))
    rect(d, 6, 2, 25, 12, C["dark"]); rect(d, 6, 2, 25, 2, (86, 92, 108))
    vgrad(d, 7, 3, 24, 11, (126, 200, 246), (56, 120, 206))
    rect(d, 7, 3, 24, 3, (40, 90, 170)); rect(d, 9, 6, 15, 6, (236, 244, 252)); rect(d, 9, 8, 19, 8, (190, 222, 248))
    im.putpixel((22, 5), (226, 240, 252)); im.putpixel((21, 6), (226, 240, 252))
    # teclado e mouse
    rect(d, 8, 16, 23, 20, (86, 92, 104)); rect(d, 8, 16, 23, 16, (120, 126, 138))
    for kx in range(9, 23, 2):
        for ky in (17, 19):
            im.putpixel((kx, ky), (196, 200, 210))
    d.ellipse([26, 16, 29, 20], fill=(250, 250, 252), outline=(150, 154, 166))
    if variant == 0:      # planta
        rect(d, 48, 13, 56, 20, C["pot"]); rect(d, 48, 13, 49, 20, shade(C["pot"], 22)); rect(d, 55, 13, 56, 20, C["pot_d"])
        rect(d, 47, 12, 57, 13, shade(C["pot"], -20))
        for cx, cy, col in ((48, 8, C["leaf_d"]), (56, 8, C["leaf_d"]), (52, 5, C["leaf"]), (49, 10, C["leaf"]), (55, 10, C["leaf"])):
            d.ellipse([cx - 3, cy - 3, cx + 3, cy + 2], fill=col)
        rect(d, 51, 4, 52, 5, C["leaf_l"]); rect(d, 48, 8, 49, 8, C["leaf_l"])
    elif variant == 1:    # papéis + caneca
        rect(d, 38, 9, 47, 19, (196, 198, 206)); rect(d, 36, 7, 45, 17, (252, 252, 254))
        for ly in (10, 12, 14):
            rect(d, 38, ly, 43, ly, (176, 180, 192))
        rect(d, 51, 9, 56, 16, (214, 72, 72)); rect(d, 51, 9, 52, 16, (236, 110, 110))
        rect(d, 51, 9, 56, 9, (120, 40, 40)); rect(d, 57, 11, 58, 14, (184, 56, 56))
    elif variant == 2:    # notebook fechado + luminária
        rect(d, 35, 10, 49, 19, (104, 110, 124)); rect(d, 35, 10, 49, 11, (150, 156, 170))
        rect(d, 41, 14, 43, 15, (170, 176, 190))
        d.ellipse([52, 15, 59, 19], fill=(80, 84, 96)); rect(d, 55, 8, 56, 16, (80, 84, 96))
        d.polygon([(51, 9), (60, 9), (58, 4), (53, 4)], fill=(250, 210, 80)); rect(d, 53, 4, 58, 4, (255, 236, 150))
    else:                 # telefone + pastas
        rect(d, 35, 7, 41, 18, (64, 112, 194)); rect(d, 35, 7, 36, 18, (100, 146, 220))
        rect(d, 42, 8, 47, 18, (232, 186, 64)); rect(d, 42, 8, 43, 18, (250, 214, 110))
        rect(d, 51, 9, 59, 18, C["dark"]); rect(d, 51, 9, 59, 9, (86, 92, 108))
        rect(d, 52, 11, 54, 16, (70, 74, 86))
        for kx in (56, 58):
            for ky in (12, 14, 16):
                im.putpixel((kx, ky), (170, 176, 190))
    return outline(im)


def chair(col, col_d, facing_up=False):
    """Cadeira de escritório; com facing_up o encosto fica embaixo (pessoa olhando para a mesa acima)."""
    im = new(); d = ImageDraw.Draw(im)
    shadow(d, [6, 23, 25, 30])
    for wx, wy in ((8, 27), (23, 27), (15, 29), (11, 24), (20, 24)):
        rect(d, wx, wy, wx + 1, wy + 1, (36, 38, 46))
    seat_y, back_y = ((5, 18), (17, 25)) if facing_up else ((10, 23), (3, 11))
    d.rounded_rectangle([9, back_y[0], 22, back_y[1]], 3, fill=col_d)
    rect(d, 11, back_y[0] + 1, 20, back_y[0] + 1, shade(col_d, 26))
    d.rounded_rectangle([8, seat_y[0], 23, seat_y[1]], 4, fill=col)
    vgrad(d, 10, seat_y[0] + 2, 21, seat_y[1] - 2, shade(col, 22), shade(col, -14))
    rect(d, 10, seat_y[0] + 1, 21, seat_y[0] + 1, shade(col, 34))
    rect(d, 6, seat_y[0] + 3, 7, seat_y[1] - 3, col_d); rect(d, 24, seat_y[0] + 3, 25, seat_y[1] - 3, col_d)
    return outline(im)


def plant(big=False):
    im = new(); d = ImageDraw.Draw(im)
    shadow(d, [7, 25, 24, 31])
    # vaso com luz à esquerda
    d.polygon([(10, 20), (21, 20), (20, 29), (11, 29)], fill=C["pot"])
    rect(d, 11, 21, 12, 28, shade(C["pot"], 24)); rect(d, 19, 21, 20, 28, C["pot_d"])
    rect(d, 9, 19, 22, 21, shade(C["pot"], 10)); rect(d, 9, 19, 22, 19, shade(C["pot"], 34))
    rect(d, 11, 20, 20, 20, (70, 50, 40))
    # folhas em leque: as de trás (baixo) escuras, as de cima claras
    cx, cy, r = 16, (12 if big else 14), (13 if big else 10)
    leaves = []
    for i in range(14):
        ang = math.radians(i * (360 / 14) + 8)
        length = r - (i % 3) * 1.5
        leaves.append((math.sin(ang), ang, length))
    for s_, ang, length in sorted(leaves, key=lambda l: -l[0]):
        tx, ty = cx + math.cos(ang) * length, cy + math.sin(ang) * length * 0.8
        nx, ny = -math.sin(ang) * 2.6, math.cos(ang) * 2.6
        mx, my = cx + math.cos(ang) * length * 0.5, cy + math.sin(ang) * length * 0.4
        col = C["leaf_d"] if s_ > 0.35 else (C["leaf_l"] if math.cos(ang) < -0.2 and s_ < 0 else C["leaf"])
        d.polygon([(cx, cy), (mx + nx, my + ny), (tx, ty), (mx - nx, my - ny)], fill=col)
        if s_ <= 0.35:
            d.line([(cx, cy), (mx, my)], fill=shade(col, 26))
    d.ellipse([cx - 3, cy - 3, cx + 3, cy + 2], fill=C["leaf"])
    return outline(im)


def bush():
    im = new(); d = ImageDraw.Draw(im)
    shadow(d, [3, 20, 28, 30])
    d.ellipse([2, 6, 29, 28], fill=C["canopy_d"]); d.ellipse([3, 4, 28, 25], fill=C["canopy"])
    d.ellipse([7, 7, 17, 15], fill=C["canopy_l"])
    return im


def tree_big():
    im = new(64, 96); d = ImageDraw.Draw(im)
    shadow(d, [8, 76, 56, 92])
    rect(d, 27, 58, 36, 86, C["trunk"]); rect(d, 27, 58, 29, 86, lighten(C["trunk"], 20))
    d.ellipse([3, 6, 61, 68], fill=C["canopy_d"])
    d.ellipse([5, 2, 59, 62], fill=C["canopy"])
    d.ellipse([12, 8, 40, 32], fill=C["canopy_l"]); d.ellipse([34, 20, 52, 36], fill=C["canopy_l"])
    noise_box = new(64, 96)
    noise(noise_box, [C["canopy_d"] + (255,)], 90, 21)
    px, npx = im.load(), noise_box.load()
    for y in range(4, 60):
        for x in range(6, 58):
            if npx[x, y][3] and px[x, y][3]:
                px[x, y] = npx[x, y]
    return im


def bookshelf(seed):
    im = new(); d = ImageDraw.Draw(im)
    rect(d, 1, 1, 30, 30, C["wood_d"]); rect(d, 3, 3, 28, 28, C["wood"])
    rng = random.Random(seed)
    for top, bot in ((4, 9), (12, 18), (21, 27)):
        rect(d, 3, bot + 1, 28, bot + 2, C["wood_d"])
        x = 4
        while x < 27:
            w = rng.randrange(2, 4)
            col = rng.choice([(200, 70, 70), (70, 120, 200), (230, 190, 70), (90, 160, 100), (230, 230, 235), (150, 90, 160)])
            rect(d, x, top + rng.randrange(0, 2), min(27, x + w - 1), bot, col)
            x += w + rng.randrange(0, 2)
    return im


def counter(kind):
    im = new(); d = ImageDraw.Draw(im)
    rect(d, 0, 3, 31, 24, (218, 220, 226)); rect(d, 0, 3, 31, 3, (240, 242, 246))
    rect(d, 0, 25, 31, 30, (176, 180, 190)); rect(d, 15, 26, 16, 29, (150, 154, 164))
    if kind == "sink":
        rect(d, 7, 8, 24, 19, (150, 158, 170)); rect(d, 9, 10, 22, 17, (120, 130, 144))
        rect(d, 15, 5, 16, 9, (110, 116, 128))
    elif kind == "stove":
        rect(d, 4, 6, 27, 21, C["dark"])
        for cx, cy in ((10, 10), (21, 10), (10, 17), (21, 17)):
            d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], outline=(120, 124, 134))
    elif kind == "coffee":
        rect(d, 10, 4, 21, 18, C["dark"]); rect(d, 12, 13, 19, 16, (90, 94, 104))
        rect(d, 18, 6, 19, 7, (230, 70, 70)); rect(d, 23, 12, 26, 16, (240, 240, 244))
    return im


def fridge():
    im = new(); d = ImageDraw.Draw(im)
    rect(d, 4, 0, 27, 30, C["white_e"]); rect(d, 5, 1, 26, 28, C["white"])
    rect(d, 5, 10, 26, 10, C["white_e"]); rect(d, 22, 3, 23, 8, (150, 154, 164)); rect(d, 22, 13, 23, 20, (150, 154, 164))
    return im


def cooler():
    im = new(); d = ImageDraw.Draw(im)
    shadow(d, [8, 25, 23, 30])
    rect(d, 10, 14, 21, 28, C["white_e"]); rect(d, 11, 15, 20, 27, C["white"])
    d.ellipse([9, 1, 22, 16], fill=(120, 190, 238)); rect(d, 12, 4, 13, 9, (190, 228, 250))
    rect(d, 14, 19, 17, 20, (70, 120, 210))
    return im


def printer():
    im = new(); d = ImageDraw.Draw(im)
    rect(d, 3, 9, 28, 27, (206, 208, 216)); rect(d, 3, 22, 28, 27, (170, 174, 184))
    rect(d, 7, 11, 24, 14, C["dark"]); rect(d, 9, 4, 22, 11, (250, 250, 252))
    rect(d, 22, 17, 24, 18, (80, 200, 120))
    return im


def cabinet():
    im = new(); d = ImageDraw.Draw(im)
    rect(d, 3, 2, 28, 29, (150, 156, 168)); rect(d, 4, 3, 27, 28, (176, 182, 194))
    for y in (11, 20):
        rect(d, 4, y, 27, y, (150, 156, 168))
    for y in (7, 15, 24):
        rect(d, 13, y, 18, y, (110, 116, 128))
    return im


def sofa_img(w):
    im = new(w, 32); d = ImageDraw.Draw(im)
    base, back = (104, 118, 146), (84, 96, 122)
    shadow(d, [2, 22, w - 3, 31])
    d.rounded_rectangle([2, 3, w - 3, 13], 3, fill=back)
    d.rounded_rectangle([2, 11, w - 3, 26], 3, fill=base)
    d.rounded_rectangle([0, 6, 6, 27], 3, fill=back); d.rounded_rectangle([w - 7, 6, w - 1, 27], 3, fill=back)
    for x in range(32, w - 8, 32):
        rect(d, x - 1, 13, x - 1, 24, back)
    rect(d, 8, 14, w - 10, 14, lighten(base, 26))
    return im


def coffee_table():
    im = new(); d = ImageDraw.Draw(im)
    shadow(d, [5, 18, 26, 27])
    d.rounded_rectangle([5, 10, 26, 24], 3, fill=C["wood_d"])
    d.rounded_rectangle([5, 9, 26, 21], 3, fill=C["wood"])
    rect(d, 12, 13, 16, 15, (240, 240, 244))
    return im


def round_table():
    im = new(); d = ImageDraw.Draw(im)
    shadow(d, [5, 14, 26, 30])
    d.ellipse([5, 7, 26, 27], fill=C["white_f"]); d.ellipse([5, 4, 26, 24], fill=C["white"], outline=C["white_e"])
    rect(d, 13, 12, 17, 15, (210, 90, 80))
    return im


def booth():
    im = new(); d = ImageDraw.Draw(im)
    rect(d, 0, 0, 31, 2, (96, 102, 116))
    rect(d, 0, 5, 20, 27, (204, 206, 214)); rect(d, 0, 28, 20, 30, (160, 164, 176))
    rect(d, 2, 9, 6, 22, C["dark"]); rect(d, 5, 10, 6, 21, C["screen"])
    rect(d, 10, 12, 12, 20, (150, 154, 164))
    return im


def sign():
    im = new(); d = ImageDraw.Draw(im)
    shadow(d, [9, 26, 22, 31])
    rect(d, 15, 16, 16, 29, C["wood_d"])
    d.rounded_rectangle([5, 3, 26, 19], 3, fill=(232, 120, 160))
    for y in (8, 12):
        rect(d, 9, y, 22, y, (252, 222, 234))
    return im


def flowers(seed):
    im = new(); d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    for _ in range(5):
        x, y = rng.randrange(4, 26), rng.randrange(8, 26)
        rect(d, x + 1, y + 2, x + 1, y + 5, C["leaf_d"])
        col = rng.choice([(230, 70, 90), (250, 210, 70), (245, 245, 250), (236, 120, 170)])
        rect(d, x, y, x + 2, y + 2, col); rect(d, x + 1, y + 1, x + 1, y + 1, (250, 230, 120))
    return im


TABLE_COLORS = {
    "white": (C["white"], C["white_e"], C["white_f"]),
    "wood": (C["wood_l"], C["wood_d"], C["wood"]),
    "gray": ((150, 156, 168), (110, 116, 128), (120, 126, 138)),
}


def table_img(color, w, h):
    top, edge, front = TABLE_COLORS[color]
    im = new(w, h); d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 7, w - 3, h - 1], 4, fill=C["shadow"])
    d.rounded_rectangle([2, 3, w - 3, h - 4], 4, fill=front)
    rect(d, 4, h - 6, w - 5, h - 6, shade(front, -16))
    d.rounded_rectangle([2, 2, w - 3, h - 9], 4, fill=top)
    vgrad(d, 4, 4, w - 5, h - 11, shade(top, 8), shade(top, -10))
    rect(d, 4, 3, w - 5, 3, shade(top, 22)); rect(d, 3, h - 9, w - 4, h - 9, edge)
    return outline(im)


LOGO_PATH = ROOT / "assets" / "maju_logo.png"


def logo_fit(max_w, max_h):
    logo = Image.open(LOGO_PATH).convert("RGBA")
    k = min(max_w / logo.width, max_h / logo.height)
    return logo.resize((max(1, round(logo.width * k)), max(1, round(logo.height * k))), Image.LANCZOS)


def logo_rug(tw, th):
    im = new(tw * T, th * T); d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 4, im.width - 3, im.height - 1], 8, fill=C["shadow"])
    d.rounded_rectangle([2, 2, im.width - 3, im.height - 4], 8, fill=(196, 160, 72))
    d.rounded_rectangle([5, 5, im.width - 6, im.height - 7], 6, fill=(250, 248, 242))
    d.rounded_rectangle([8, 8, im.width - 9, im.height - 10], 5, outline=(222, 200, 140))
    logo = logo_fit(im.width - 28, im.height - 26)
    im.alpha_composite(logo, ((im.width - logo.width) // 2, (im.height - 4 - logo.height) // 2))
    return im


def logo_wall(tw):
    im = new(tw * T, T)
    for i in range(tw):
        im.paste(face("plain"), (i * T, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([3, 3, im.width - 4, 24], 3, fill=(250, 250, 252), outline=(196, 160, 72))
    logo = logo_fit(im.width - 14, 18)
    im.alpha_composite(logo, ((im.width - logo.width) // 2, 5 + (18 - logo.height) // 2))
    return im


_LABEL_FONT = None


def label_img(text):
    global _LABEL_FONT
    if _LABEL_FONT is None:
        try:
            _LABEL_FONT = ImageFont.truetype("arialbd.ttf", 13)
        except OSError:
            _LABEL_FONT = ImageFont.load_default()
    probe = ImageDraw.Draw(new())
    x0, y0, x1, y1 = probe.textbbox((0, 0), text, font=_LABEL_FONT)
    tiles = math.ceil((x1 - x0 + 8) / T)
    im = new(tiles * T, T); d = ImageDraw.Draw(im)
    tx = (im.width - (x1 - x0)) // 2 - x0
    ty = (T - (y1 - y0)) // 2 - y0
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1), (1, 1)):
        d.text((tx + ox, ty + oy), text, font=_LABEL_FONT, fill=(24, 28, 40, 230))
    d.text((tx, ty), text, font=_LABEL_FONT, fill=(250, 250, 252, 255))
    return im


# ---------------------------------------------------------------- registro de tiles

NON_COLLIDING = ("grass", "dgrass", "flowers", "stone", "wood_", "tile_", "slate", "chair", "sofa",
                 "armchair", "label", "logo_rug", "tree_top", "start")
_big = {}


def big(key, fn):
    if key not in _big:
        _big[key] = fn()
    return _big[key]


def crop(im, i, j):
    return im.crop((i * T, j * T, i * T + T, j * T + T))


def make_tile(name):
    kind, _, arg = name.partition(":")
    simple = {
        "wall": wall_top, "cliff": cliff, "bush": lambda: outline(bush()), "cooler": lambda: outline(cooler()), "printer": lambda: outline(printer()),
        "cabinet": lambda: outline(cabinet()), "fridge": fridge, "coffee_table": lambda: outline(coffee_table()), "round_table": lambda: outline(round_table()),
        "booth_l": booth, "booth_r": lambda: ImageOps.mirror(booth()), "sign": lambda: outline(sign()),
        "armchair": lambda: outline(sofa_img(32)), "start": new,
        "stone": lambda: pavers(C["stone"], C["stone_d"], C["stone_l"]),
        "tile_gray": lambda: pavers(C["tg"], C["tg_d"], C["tg_l"]),
        "slate": lambda: pavers(C["sl"], C["sl_d"], C["sl_l"], 32),
        "plant": plant, "plant_big": lambda: plant(True),
        "chair": lambda: chair(C["chair"], C["chair_d"]),
        "chair_up": lambda: chair(C["chair"], C["chair_d"], facing_up=True),
        "chair_yellow": lambda: chair(C["yellow"], C["yellow_d"]),
        "chair_white": lambda: chair(C["cw"], C["cw_d"]),
    }
    if kind in simple:
        return simple[kind]()
    if kind == "grass":
        return grass(int(arg))
    if kind == "grass_fl":
        return grass_flowers(int(arg))
    if kind == "dgrass":
        return dark_grass(int(arg))
    if kind == "water":
        return water(int(arg))
    if kind == "wood_light":
        return planks(C["wl"], C["wl_d"], C["wl_l"], int(arg))
    if kind == "wood_dark":
        return planks(C["wd"], C["wd_d"], C["wd_l"], int(arg))
    if kind == "face":
        return face(arg)
    if kind == "ext":
        return ext_face(arg == "win")
    if kind == "desk":
        v, _, i = arg.partition(":")
        return crop(big(f"desk-{v}", lambda: desk(int(v))), int(i), 0)
    if kind == "shelf":
        return bookshelf(int(arg))
    if kind == "counter":
        return counter(arg)
    if kind == "flowers":
        return flowers(int(arg))
    if kind in ("tree_top", "tree_base"):
        i = int(arg)
        return crop(big("tree", lambda: outline(tree_big())), i % 2, i // 2 if kind == "tree_top" else 2)
    if kind == "sofa":
        return crop(big("sofa", lambda: outline(sofa_img(64))), int(arg), 0)
    if kind == "table":                      # table:cor:forma:i:j
        color, shape, i, j = arg.split(":")
        w, h = {"9": (96, 96), "h": (96, 32), "v": (32, 96), "s": (32, 32)}[shape]
        return crop(big(f"table-{color}-{shape}", lambda: table_img(color, w, h)), int(i), int(j))
    if kind == "logo_rug":
        i, j = map(int, arg.split(":"))
        return crop(big("logo_rug", lambda: logo_rug(LOGO_RUG[2], LOGO_RUG[3])), i, j)
    if kind == "logo_wall":
        w, i = map(int, arg.split(":"))
        return crop(big(f"logo_wall-{w}", lambda: logo_wall(w)), i, 0)
    if kind == "label":                      # label:texto:i
        text, _, i = arg.rpartition(":")
        return crop(big(f"label-{text}", lambda: label_img(text)), int(i), 0)
    raise KeyError(name)


class Atlas:
    def __init__(self):
        self.images, self.gids, self.collides = [], {}, []

    def gid(self, name):
        if name not in self.gids:
            self.images.append(make_tile(name))
            self.gids[name] = len(self.images)
            if not name.startswith(NON_COLLIDING):
                self.collides.append(len(self.images) - 1)
        return self.gids[name]

    def image(self):
        rows = math.ceil(len(self.images) / ATLAS_COLS)
        im = new(ATLAS_COLS * T, rows * T)
        for k, tile in enumerate(self.images):
            im.paste(tile, ((k % ATLAS_COLS) * T, (k // ATLAS_COLS) * T))
        return im


# ------------------------------------------------------------------------ layout
#
# Tudo espaçado pensando na conversa por proximidade do WorkAdventure: estações de trabalho
# a 5 tiles (160 px) uma da outra e grupos de mesas separados por corredores largos.

# Salas (interior): x0, y0, x1, y1, piso. As paredes nascem em volta de cada sala.
ROOMS = [
    (24, 3, 42, 10, "wood_dark"),    # auditório (topo)
    (44, 3, 57, 10, "tile_gray"),    # recepção (entrada)
    (24, 12, 57, 44, "wood_light"),  # salão principal
    (8, 18, 22, 40, "wood_dark"),    # ala de reuniões (esquerda)
    (8, 41, 22, 44, "wood_light"),   # faixa de passagem
    (59, 12, 64, 17, "wood_dark"),   # escritório 1
    (66, 12, 72, 17, "wood_dark"),   # escritório Dra Júlia
    (59, 19, 72, 20, "wood_light"),  # corredor
    (59, 22, 72, 31, "tile_gray"),   # lunchroom
    (59, 33, 66, 44, "wood_light"),  # jurídico - Silvio
    (50, 46, 66, 54, "wood_dark"),   # sala do dono (diretoria)
    (24, 46, 48, 55, "wood_light"),  # sala inferior
]
CORRIDOR = {(x, y) for x in range(59, 73) for y in (19, 20)}   # corredor aberto: sem face de parede
DOORS = ([(x, 11) for x in (32, 33, 34)] + [(x, 11) for x in (53, 54, 55)]          # auditório, recepção
         + [(45, 2), (46, 2)]                                                        # porta da rua
         + [(23, y) for y in range(26, 45)]                                          # ala de reuniões
         + [(61, 18), (69, 18), (58, 19), (58, 20), (58, 27), (58, 28), (58, 37), (58, 38)]
         + [(x, 45) for x in range(33, 39)] + [(55, 45), (56, 45)])                 # sala inferior, diretoria

FACE_DECOR = {
    (25, 12): "green", (26, 12): "green", (44, 12): "green", (45, 12): "green", (57, 12): "tv",
    (10, 18): "green", (11, 18): "green", (12, 18): "green", (13, 18): "green",
    (17, 18): "board", (18, 18): "board",
    (69, 22): "tv", (70, 22): "tv", (71, 22): "tv",
    (63, 33): "art", (64, 46): "art",
    **{(x, 46): "blue" for x in (26, 29, 41, 44, 47)},
}

WORK_COLS = (26, 31, 36, 41)          # x da mesa (2 tiles); a cadeira fica em (x, y + 1)
WORK_ROWS = (15, 20, 25, 32, 37)      # 3 fileiras no Cível, 2 no Setor Pernambuco
MEETING_ROWS = (15, 23, 31, 39)       # mesas de reunião do salão (2x2, coluna x 48-49)
WING_ROWS = (21, 29, 37)              # mesas da ala de reuniões (3x2, x 13-15)

LABELS = [("CÍVEL", 34.5, 29), ("SETOR PERNAMBUCO", 34.5, 41), ("Dra Júlia", 69.5, 20),
          ("LUNCHROOM", 65.5, 30), ("JURÍDICO - SILVIO", 62.5, 43), ("DIRETORIA", 58, 53),
          ("RECEPÇÃO", 50.5, 10)]

LOGO_RUG = (47, 7, 7, 3)              # x, y, largura e altura em tiles (piso da recepção)
LOGO_WALLS = [(49, 3, 6), (51, 46, 4)]  # x, y, largura: parede da recepção e da diretoria

AREAS = (
    [("Auditório", 24, 3, 42, 10, {"jitsiRoom": "auditorio"})]
    + [(f"Reunião {i}", 12, r - 1, 16, r + 2, {"jitsiRoom": f"reuniao-{i}"}) for i, r in enumerate(WING_ROWS, 1)]
    + [(f"Reunião salão {i}", 47, r - 1, 50, r + 2, {"jitsiRoom": f"reuniao-salao-{i}"})
       for i, r in enumerate(MEETING_ROWS, 1)]
    + [("Lunchroom", 59, 22, 72, 31, {"silent": True})]
)

SPAWN = [(x, y) for x in (55, 56) for y in (8, 9)]   # recepção: entrada padrão (convidados)
ENTRIES = []                                        # (nome, x, y, descrição) preenchido em build()


def build():
    rng = random.Random(42)
    layers = {k: [[None] * W for _ in range(H)] for k in ("floor", "walls", "furniture", "labels", "above", "start")}

    def put(layer, x, y, name):
        if 0 <= x < W and 0 <= y < H:
            layers[layer][y][x] = name

    inside = lambda x, y: 0 <= x < W and 0 <= y < H

    interior = {}
    for x0, y0, x1, y1, f in ROOMS:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                interior[(x, y)] = f
    for c in DOORS:
        interior[c] = "wood_light"
    footprint = {(x, y) for x0, y0, x1, y1, _ in ROOMS
                 for y in range(y0 - 1, y1 + 2) for x in range(x0 - 1, x1 + 2) if inside(x, y)}
    walls = footprint - interior.keys()
    ext_faces = {(x, y + 1) for x, y in walls if inside(x, y + 1) and (x, y + 1) not in footprint}

    # ---- terreno externo
    water_cells = {(0, y) for y in range(10, H)}
    water_cells |= {(x, y) for y in range(H) for x in range(W)
                    if ((x - 11.5) / 7.2) ** 2 + ((y - 56.5) / 6.2) ** 2 <= 1}
    cliff_cells = {(1, y) for y in range(9, H)} | {(0, 9)}
    stone_cells = {(x, y) for x in (45, 46) for y in range(0, 2)}
    near_building = {(x + dx, y + dy) for x, y in footprint | ext_faces for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    blocked_out = footprint | water_cells | cliff_cells | stone_cells | ext_faces
    patches = [(rng.uniform(2, W - 2), rng.uniform(2, H - 2), rng.uniform(1.8, 3.4)) for _ in range(26)]
    dark = {(x, y) for y in range(H) for x in range(W) if (x, y) not in blocked_out
            and any(math.hypot(x - cx, y - cy) <= r for cx, cy, r in patches)}

    def mask(cells, x, y):
        m = 0
        for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
            nx, ny = x + dx, y + dy
            if inside(nx, ny) and (nx, ny) not in cells:
                m |= bit
        return m

    for y in range(H):
        for x in range(W):
            c = (x, y)
            if c in interior:
                f = interior[c]
                put("floor", x, y, f"{f}:{rng.randrange(3)}" if f.startswith("wood") else f)
            elif c in walls:
                put("walls", x, y, "wall")
            elif c in water_cells:
                put("floor", x, y, f"water:{mask(water_cells, x, y)}")
            elif c in cliff_cells:
                put("floor", x, y, "cliff")
            elif c in stone_cells:
                put("floor", x, y, "stone")
            elif c in dark:
                put("floor", x, y, f"dgrass:{mask(dark, x, y)}")
            else:
                put("floor", x, y, f"grass_fl:{rng.randrange(3)}" if rng.random() < 0.05 else f"grass:{rng.randrange(4)}")

    for (x, y) in interior:
        if (x, y) not in DOORS and (x, y) not in CORRIDOR and (x, y - 1) in walls:
            put("walls", x, y, f"face:{FACE_DECOR.get((x, y), 'plain')}")
    for (x, y) in ext_faces:
        put("walls", x, y, "ext:win" if x % 3 == 1 else "ext:plain")
    for lx, ly, lw in LOGO_WALLS:
        for i in range(lw):
            put("walls", lx + i, ly, f"logo_wall:{lw}:{i}")

    # ---- vegetação externa (espalhada, longe das paredes e da água)
    used = set(near_building)
    trees = 0
    for _ in range(4000):
        if trees >= 30:
            break
        tx, ty = rng.randrange(1, W - 2), rng.randrange(0, H - 3)
        cells = {(tx + i, ty + j) for i in range(2) for j in range(3)}
        halo = {(x + dx, y + dy) for x, y in cells for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        if any(not inside(*c) or c in blocked_out or c in used for c in halo if inside(*c)):
            continue
        used |= halo; trees += 1
        for i in range(2):
            put("above", tx + i, ty, f"tree_top:{i}")
            put("above", tx + i, ty + 1, f"tree_top:{i + 2}")
            put("furniture", tx + i, ty + 2, f"tree_base:{i}")
    bushes = 0
    for _ in range(4000):
        if bushes >= 22:
            break
        bx, by = rng.randrange(2, W), rng.randrange(0, H)
        if (bx, by) in blocked_out or (bx, by) in used:
            continue
        put("furniture", bx, by, "bush"); used.add((bx, by)); bushes += 1
    put("furniture", 10, 12, "sign")
    for x in range(11, 16):
        put("furniture", x, 12, f"flowers:{x}")

    # ---- mobiliário
    def table(color, x0, y0, x1, y1):
        w, h = x1 - x0 + 1, y1 - y0 + 1
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                i = 0 if x == x0 else (2 if x == x1 else 1)
                j = 0 if y == y0 else (2 if y == y1 else 1)
                if w > 1 and h > 1:
                    put("furniture", x, y, f"table:{color}:9:{i}:{j}")
                elif h == 1 and w > 1:
                    put("furniture", x, y, f"table:{color}:h:{i}:0")
                elif w == 1 and h > 1:
                    put("furniture", x, y, f"table:{color}:v:0:{j}")
                else:
                    put("furniture", x, y, f"table:{color}:s:0:0")

    def ring(x0, y0, x1, y1, chair_name, sides="nsew"):
        """Cadeiras em volta de uma mesa."""
        for x in range(x0, x1 + 1):
            if "n" in sides: put("furniture", x, y0 - 1, chair_name)
            if "s" in sides: put("furniture", x, y1 + 1, chair_name)
        for y in range(y0, y1 + 1):
            if "w" in sides: put("furniture", x0 - 1, y, chair_name)
            if "e" in sides: put("furniture", x1 + 1, y, chair_name)

    f = lambda x, y, n: put("furniture", x, y, n)

    # auditório
    for y in range(5, 10):
        for x in (26, 27, 28, 29, 31, 32, 33, 34, 35):
            f(x, y, "chair")
    table("wood", 38, 5, 39, 7)
    f(41, 4, "plant_big"); f(24, 9, "plant"); f(41, 9, "plant")

    # salão principal: estações individuais a 5 tiles (160 px) uma da outra
    ENTRIES.clear()
    for k, (x, y) in enumerate((x, y) for y in WORK_ROWS for x in WORK_COLS):
        v = (k * 3 + y) % 4
        f(x, y, f"desk:{v}:0"); f(x + 1, y, f"desk:{v}:1"); f(x, y + 1, "chair_up")
        setor = "Cível" if y < 30 else "Setor Pernambuco"
        ENTRIES.append((f"mesa-{k + 1:02d}", x, y + 1, f"{setor}, fileira {WORK_ROWS.index(y) + 1}, "
                        f"posição {WORK_COLS.index(x) + 1}"))
    for ty in MEETING_ROWS:
        table("white", 48, ty, 49, ty + 1)
        ring(48, ty, 49, ty + 1, "chair")
    f(28, 13, "cooler"); f(38, 13, "printer"); f(39, 13, "cabinet"); f(51, 13, "cabinet")
    f(57, 13, "plant_big"); f(24, 13, "plant_big"); f(45, 44, "plant"); f(57, 44, "plant_big")
    f(24, 29, "plant"); f(44, 29, "plant"); f(24, 41, "plant"); f(44, 41, "plant")
    rx, ry, rw, rh = LOGO_RUG
    for j in range(rh):
        for i in range(rw):
            put("labels", rx + i, ry + j, f"logo_rug:{i}:{j}")

    # recepção
    table("wood", 49, 5, 53, 5); f(51, 4, "chair")
    f(44, 4, "cooler"); f(57, 4, "plant_big"); f(44, 10, "plant"); f(57, 10, "plant")
    f(44, 7, "sofa:0"); f(45, 7, "sofa:1"); f(44, 9, "armchair")
    f(56, 5, "sofa:0"); f(57, 5, "sofa:1")

    # ala de reuniões
    for ty in WING_ROWS:
        table("white", 13, ty, 15, ty + 1)
        ring(13, ty, 15, ty + 1, "chair")
    f(8, 19, "plant_big"); f(22, 19, "plant"); f(8, 25, "plant"); f(8, 33, "plant"); f(8, 40, "plant_big"); f(22, 40, "plant")

    # escritório 1
    f(59, 12, "shelf:1"); f(60, 12, "shelf:2"); f(64, 13, "plant")
    table("white", 61, 14, 62, 14); f(61, 13, "chair"); f(61, 15, "chair_white"); f(62, 15, "chair_white")
    # escritório Dra Júlia
    f(66, 12, "shelf:3"); f(67, 12, "shelf:4"); f(72, 13, "plant")
    table("white", 69, 14, 70, 14); f(69, 13, "chair"); f(69, 15, "chair_white"); f(70, 15, "chair_white")

    # lunchroom (área silenciosa)
    for x, kind in zip(range(59, 65), ("plain", "sink", "stove", "coffee", "plain", "plain")):
        f(x, 22, f"counter:{kind}")
    f(66, 23, "fridge")
    table("gray", 63, 26, 68, 27)
    ring(63, 26, 68, 27, "chair_yellow")
    f(59, 31, "plant"); f(72, 31, "plant_big"); f(72, 24, "plant")

    # jurídico - Silvio
    f(59, 33, "shelf:5"); f(60, 33, "shelf:6"); f(66, 34, "plant")
    table("white", 61, 36, 63, 36); f(62, 35, "chair")
    for x in (61, 62, 63):
        f(x, 37, "chair_white")
    f(60, 41, "sofa:0"); f(61, 41, "sofa:1"); f(63, 41, "coffee_table"); f(65, 41, "armchair")
    f(66, 44, "plant"); f(59, 44, "plant")

    # sala do dono (diretoria)
    f(57, 46, "shelf:7"); f(58, 46, "shelf:8"); f(59, 46, "shelf:9")
    table("wood", 57, 49, 59, 49); f(58, 48, "chair")
    f(57, 50, "chair_white"); f(59, 50, "chair_white")
    f(62, 51, "sofa:0"); f(63, 51, "sofa:1"); f(64, 52, "coffee_table"); f(65, 51, "armchair")
    f(50, 47, "plant_big"); f(66, 47, "plant_big"); f(50, 54, "plant"); f(66, 54, "plant")

    # sala inferior
    for y in (47, 52):                       # baias espaçadas (5 tiles)
        f(24, y, "booth_l"); f(25, y, "chair_white")
        f(48, y, "booth_r"); f(47, y, "chair_white")
    for tx, ty in ((30, 48), (36, 48), (42, 48), (30, 53), (36, 53), (42, 53)):
        f(tx, ty, "round_table"); f(tx - 1, ty, "chair_white"); f(tx + 1, ty, "chair_white")
    f(24, 55, "plant"); f(48, 55, "plant"); f(24, 50, "plant"); f(48, 50, "plant")

    # ---- rótulos
    for text, cx, row in LABELS:
        n = label_img(text).width // T
        start = round(cx - n / 2)
        for i in range(n):
            put("labels", start + i, row, f"label:{text}:{i}")

    ENTRIES.extend([
        ("baia-1", 25, 47, "Sala inferior, baia esquerda de cima"), ("baia-2", 25, 52, "Sala inferior, baia esquerda de baixo"),
        ("baia-3", 47, 47, "Sala inferior, baia direita de cima"), ("baia-4", 47, 52, "Sala inferior, baia direita de baixo"),
        ("escritorio-1", 61, 13, "Escritório 1"), ("dra-julia", 69, 13, "Escritório Dra Júlia"),
        ("juridico-silvio", 62, 35, "Jurídico - Silvio"), ("diretoria", 58, 48, "Diretoria"),
    ])

    # ---- spawn
    for x, y in SPAWN:
        put("start", x, y, "start")

    return layers


# ------------------------------------------------------------------------ saída

LAYER_ORDER = ["floor", "walls", "furniture", "labels", "floorLayer", "above", "start"]


def write_outputs(layers):
    atlas = Atlas()
    data = {k: [atlas.gid(n) if n else 0 for row in rows for n in row] for k, rows in layers.items()}

    tileset_png = ROOT / "tilesets" / "escritorio.png"
    tileset_png.parent.mkdir(exist_ok=True)
    sheet = atlas.image()
    sheet.save(tileset_png)

    objects = []
    for k, (name, x0, y0, x1, y1, props) in enumerate(AREAS, start=1):
        objects.append({
            "id": k, "name": name, "type": "area", "class": "area",
            "x": x0 * T, "y": y0 * T, "width": (x1 - x0 + 1) * T, "height": (y1 - y0 + 1) * T,
            "rotation": 0, "visible": True,
            "properties": [{"name": key, "type": "bool" if isinstance(val, bool) else "string", "value": val}
                           for key, val in props.items()],
        })

    tmj_layers = []
    for lid, name in enumerate(LAYER_ORDER, start=1):
        if name == "floorLayer":
            tmj_layers.append({"id": lid, "name": name, "type": "objectgroup", "draworder": "topdown",
                               "objects": objects, "opacity": 1, "visible": True, "x": 0, "y": 0})
        else:
            tmj_layers.append({"id": lid, "name": name, "type": "tilelayer", "width": W, "height": H,
                               "data": data[name], "opacity": 1, "visible": True, "x": 0, "y": 0})

    start_gid = atlas.gid("start")
    for name, ex, ey, _ in ENTRIES:
        layer_data = [0] * (W * H); layer_data[ey * W + ex] = start_gid
        tmj_layers.append({"id": len(tmj_layers) + 1, "name": name, "type": "tilelayer", "width": W, "height": H,
                           "data": layer_data, "opacity": 1, "visible": True, "x": 0, "y": 0,
                           "properties": [{"name": "startLayer", "type": "bool", "value": True}]})

    tmj = {
        "compressionlevel": -1, "type": "map", "version": "1.10", "tiledversion": "1.10.2",
        "orientation": "orthogonal", "renderorder": "right-down", "infinite": False,
        "width": W, "height": H, "tilewidth": T, "tileheight": T,
        "nextlayerid": len(tmj_layers) + 1, "nextobjectid": len(objects) + 1,
        "properties": [
            {"name": "mapName", "type": "string", "value": "Escritório"},
            {"name": "mapDescription", "type": "string", "value": "Escritório virtual"},
        ],
        "layers": tmj_layers,
        "tilesets": [{
            "firstgid": 1, "name": "escritorio", "image": "tilesets/escritorio.png",
            "imagewidth": sheet.width, "imageheight": sheet.height,
            "tilewidth": T, "tileheight": T, "tilecount": len(atlas.images), "columns": ATLAS_COLS,
            "margin": 0, "spacing": 0,
            "tiles": [{"id": i, "properties": [{"name": "collides", "type": "bool", "value": True}]}
                      for i in atlas.collides],
        }],
    }
    (ROOT / "escritorio.tmj").write_text(json.dumps(tmj, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- prévias
    preview = Image.new("RGBA", (W * T, H * T), (0, 0, 0, 255))
    for name in ("floor", "walls", "furniture", "labels", "above"):
        for k, gid in enumerate(data[name]):
            if gid:
                tile = atlas.images[gid - 1]
                preview.alpha_composite(tile, ((k % W) * T, (k // W) * T))
    preview.convert("RGB").save(ROOT / "preview.png")
    preview.convert("RGB").resize((W * T * 2, H * T * 2), Image.NEAREST).save(ROOT / "preview_2x.png")

    overlay = new(W * T, H * T); d = ImageDraw.Draw(overlay)
    font = ImageFont.truetype("arialbd.ttf", 14)
    for name, x0, y0, x1, y1, props in AREAS:
        box = [x0 * T, y0 * T, (x1 + 1) * T - 1, (y1 + 1) * T - 1]
        col = (255, 140, 40) if "jitsiRoom" in props else (90, 170, 255)
        d.rectangle(box, fill=col + (70,), outline=col + (255,), width=2)
        text = f"jitsi: {props['jitsiRoom']}" if "jitsiRoom" in props else "silenciosa"
        d.text((box[0] + 4, box[1] + 3), text, font=font, fill=(255, 255, 255, 255),
               stroke_width=2, stroke_fill=(0, 0, 0, 255))
    for k, gid in enumerate(data["start"]):
        if gid:
            x, y = (k % W) * T, (k // W) * T
            d.rectangle([x, y, x + T - 1, y + T - 1], fill=(60, 220, 120, 110), outline=(60, 220, 120, 255))
    small = ImageFont.truetype("arialbd.ttf", 11)
    for name, ex, ey, _ in ENTRIES:
        x, y = ex * T, ey * T
        d.rectangle([x, y, x + T - 1, y + T - 1], fill=(230, 60, 200, 90), outline=(230, 60, 200, 255), width=2)
        d.text((x + T // 2, y + T + 1), name, font=small, anchor="mt", fill=(255, 255, 255, 255),
               stroke_width=2, stroke_fill=(0, 0, 0, 255))
    preview_areas = preview.copy(); preview_areas.alpha_composite(overlay)
    preview_areas.convert("RGB").save(ROOT / "preview_areas.png")

    lines = ["# Pontos de entrada", "",
             "Entrada padrão (sem `#`): **recepção** — é onde nascem os convidados.", "",
             "Para a pessoa nascer na própria mesa, use o link do mapa com `#nome-do-ponto` no final,",
             "por exemplo `.../escritorio.tmj#mesa-07`.", "",
             "| Ponto | Onde fica | Pessoa |", "|---|---|---|"]
    lines += [f"| `{name}` | {desc} | |" for name, _, _, desc in ENTRIES]
    (ROOT / "PONTOS_DE_ENTRADA.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"tiles: {len(atlas.images)}  colisão: {len(atlas.collides)}  áreas: {len(objects)}  entradas: {len(ENTRIES)}")
    check_reachability(data, set(atlas.collides))
    check_spacing(layers)


def check_spacing(layers):
    """Distância mínima (em tiles) entre uma estação de trabalho e qualquer outra cadeira."""
    furn = layers["furniture"]
    chairs = [(x, y) for y in range(H) for x in range(W) if (furn[y][x] or "").startswith("chair")]
    solo = [(x, y) for x, y in chairs if furn[y][x] == "chair_up"
            or (x > 0 and (furn[y][x - 1] or "").startswith("booth")) or (furn[y][x + 1] or "").startswith("booth")]
    worst = min(math.hypot(ax - bx, ay - by) for ax, ay in solo for bx, by in chairs if (ax, ay) != (bx, by))
    print(f"estações individuais: {len(solo)}  menor distância até outra cadeira: {worst:.1f} tiles ({worst * T:.0f} px)")
    between = min(math.hypot(ax - bx, ay - by) for ax, ay in solo for bx, by in solo if (ax, ay) != (bx, by))
    print(f"menor distância entre duas estações: {between:.1f} tiles ({between * T:.0f} px)")


def check_reachability(data, collides):
    """Confere se, a partir do spawn, dá para chegar em todas as áreas."""
    blocked = {k for name in ("floor", "walls", "furniture") for k, gid in enumerate(data[name])
               if gid and gid - 1 in collides}
    todo = [k for k, gid in enumerate(data["start"]) if gid]
    seen = set(todo)
    while todo:
        k = todo.pop(); x, y = k % W, k // W
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            nk = ny * W + nx
            if 0 <= nx < W and 0 <= ny < H and nk not in seen and nk not in blocked:
                seen.add(nk); todo.append(nk)
    ok = True
    rooms = [(f"sala {x0},{y0}", x0, y0, x1, y1, None) for x0, y0, x1, y1, _ in ROOMS]
    for name, x0, y0, x1, y1, _ in AREAS + rooms:
        cells = [y * W + x for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
        reach = sum(1 for k in cells if k in seen)
        free = sum(1 for k in cells if k not in blocked)
        if reach < free:
            ok = False
            print(f"  ATENÇÃO {name}: {reach}/{free} tiles livres alcançáveis")
    for name, ex, ey, _ in ENTRIES:
        if ey * W + ex not in seen:
            ok = False
            print(f"  ATENÇÃO ponto de entrada {name} bloqueado")
    print("caminhos: todas as salas e entradas alcançáveis a partir da recepção" if ok else "caminhos: há bloqueios")


if __name__ == "__main__":
    write_outputs(build())
