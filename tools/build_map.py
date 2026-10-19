#!/usr/bin/env python3
"""Gera o mapa do escritório (Tiled / WorkAdventure) com os tilesets oficiais do WorkAdventure.

Uso:  python tools/build_map.py
Saída: escritorio.tmj, tilesets/amz.png (logo e rótulos), preview*.png, PONTOS_DE_ENTRADA.md

Os tilesets oficiais ficam em tilesets/wa/ (licença em tilesets/wa/LICENSE.assets).
"""
import json
import math
import random

from PIL import Image, ImageDraw, ImageFont, ImageOps

from wa_tiles import ROOT, T, WA_TILESETS, parse, tile_image, ts_columns, ts_count, ts_image

W, H = 84, 64
FLIP = 0x80000000

# ------------------------------------------------------------------------ layout
#
# Espaçado pensando na conversa por proximidade do WorkAdventure: estações de trabalho
# a 5 tiles (160 px) uma da outra e grupos de mesas separados por corredores largos.
# As paredes do WorkAdventure têm face de 2 tiles: as duas primeiras linhas de cada sala são parede.

FLOORS = {"hall": "R350", "wood": "R353", "dark": "R352", "carpet": "R360", "tile": "R358",
          "stripes": "R383", "exec": "R377"}

# Salas (interior): x0, y0, x1, y1, piso. As paredes nascem em volta de cada sala.
ROOMS = [
    (24, 3, 42, 10, "carpet"),      # auditório
    (44, 3, 57, 10, "tile"),        # recepção (entrada)
    (24, 12, 57, 44, "hall"),       # salão principal
    (8, 18, 22, 40, "wood"),        # ala de reuniões
    (8, 41, 22, 44, "hall"),        # faixa de passagem
    (59, 12, 64, 17, "dark"),       # escritório 1
    (66, 12, 72, 17, "dark"),       # escritório Dra Júlia
    (59, 19, 72, 20, "hall"),       # corredor
    (59, 22, 72, 31, "stripes"),    # lunchroom
    (59, 33, 66, 44, "hall"),       # jurídico - Silvio
    (50, 46, 66, 54, "exec"),       # diretoria
    (24, 46, 48, 55, "hall"),       # sala inferior
]
CORRIDOR = {(x, y) for x in range(59, 73) for y in (19, 20)}     # corredor aberto: sem face de parede
DOORS = ([(x, 11) for x in (32, 33, 34)] + [(x, 11) for x in (53, 54, 55)] + [(45, 2), (46, 2)]
         + [(23, y) for y in range(26, 45)]
         + [(61, 18), (69, 18), (58, 19), (58, 20), (58, 27), (58, 28), (58, 37), (58, 38)]
         + [(x, 45) for x in range(33, 39)] + [(55, 45), (56, 45)])

WORK_COLS = (26, 31, 36, 41)          # x da mesa (3x2 tiles); a cadeira fica em (x + 1, y + 2)
WORK_ROWS = (15, 20, 25, 32, 37)      # 5 fileiras de 4 mesas no salão
MEETING_ROWS = (15, 23, 31, 39)       # mesas de vidro do salão (2x4, x 48-49)
WING_ROWS = (21, 29, 37)              # mesas da ala de reuniões (3x3, x 13-15)

LABELS = [("Dra Júlia", 69.5, 20), ("LUNCHROOM", 65.5, 31), ("JURÍDICO - SILVIO", 62.5, 44)]

AREAS = (
    [("Auditório", 24, 3, 42, 10, {"jitsiRoom": "auditorio"})]
    + [(f"Reunião {i}", 11, r - 1, 17, r + 3, {"jitsiRoom": f"reuniao-{i}"}) for i, r in enumerate(WING_ROWS, 1)]
    + [(f"Reunião salão {i}", 47, r - 1, 50, r + 4, {"jitsiRoom": f"reuniao-salao-{i}"})
       for i, r in enumerate(MEETING_ROWS, 1)]
    + [("Lunchroom", 59, 22, 72, 31, {"silent": True})]
)

SPAWN = [(x, y) for x in (55, 56) for y in (8, 9)]   # recepção: entrada padrão (convidados)

LAYERS = ["start", "collisions", "floor", "floor2", "walls", "deco1", "deco2",
          "furniture1", "furniture2", "furniture3", "labels", "floorLayer", "above1", "above2"]
HIDDEN = ("start", "collisions")      # ficam por baixo do piso, como no mapa oficial


# ------------------------------------------------------------------- tileset próprio (logo/rótulos)

LOGO_PATH = ROOT / "assets" / "maju_logo.png"
_custom = {}        # referência -> imagem 32x32


def new(w=T, h=T):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def logo_fit(max_w, max_h):
    logo = Image.open(LOGO_PATH).convert("RGBA")
    k = min(max_w / logo.width, max_h / logo.height)
    return logo.resize((max(1, round(logo.width * k)), max(1, round(logo.height * k))), Image.LANCZOS)


def logo_rug(tw, th):
    im = new(tw * T, th * T); d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 4, im.width - 3, im.height - 1], 8, fill=(0, 0, 0, 50))
    d.rounded_rectangle([2, 2, im.width - 3, im.height - 4], 8, fill=(196, 160, 72))
    d.rounded_rectangle([5, 5, im.width - 6, im.height - 7], 6, fill=(250, 248, 242))
    d.rounded_rectangle([8, 8, im.width - 9, im.height - 10], 5, outline=(222, 200, 140))
    logo = logo_fit(im.width - 28, im.height - 26)
    im.alpha_composite(logo, ((im.width - logo.width) // 2, (im.height - 4 - logo.height) // 2))
    return im


def logo_plaque(tw, th):
    """Placa para a face da parede (2 tiles de altura)."""
    im = new(tw * T, th * T); d = ImageDraw.Draw(im)
    d.rounded_rectangle([3, 5, im.width - 4, im.height - 12], 4, fill=(252, 252, 253), outline=(196, 160, 72), width=2)
    logo = logo_fit(im.width - 18, im.height - 24)
    im.alpha_composite(logo, ((im.width - logo.width) // 2, 5 + (im.height - 17 - logo.height) // 2))
    return im


def label_img(text):
    font = ImageFont.truetype("arialbd.ttf", 13)
    x0, y0, x1, y1 = ImageDraw.Draw(new()).textbbox((0, 0), text, font=font)
    tiles = math.ceil((x1 - x0 + 8) / T)
    im = new(tiles * T, T); d = ImageDraw.Draw(im)
    tx, ty = (im.width - (x1 - x0)) // 2 - x0, (T - (y1 - y0)) // 2 - y0
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1), (1, 1)):
        d.text((tx + ox, ty + oy), text, font=font, fill=(24, 28, 40, 230))
    d.text((tx, ty), text, font=font, fill=(250, 250, 252, 255))
    return im


def custom_block(name, im):
    """Fatia uma imagem em tiles 'AM:nome:i:j' e devolve as referências por posição."""
    refs = {}
    for j in range(im.height // T):
        for i in range(im.width // T):
            ref = f"AM:{name}:{i}:{j}"
            _custom[ref] = im.crop((i * T, j * T, i * T + T, j * T + T))
            refs[(i, j)] = ref
    return refs


# ------------------------------------------------------------------------ cena

class Map:
    def __init__(self):
        self.layers = {n: [[None] * W for _ in range(H)] for n in LAYERS}
        self.blocked = set()
        self.chairs = []          # (x, y, grupo) para a checagem de espaçamento
        self.entries = []         # (nome, x, y, descrição)

    def put(self, layer, x, y, ref, block=False):
        if ref and 0 <= x < W and 0 <= y < H:
            self.layers[layer][y][x] = ref
            if block:
                self.blocked.add((x, y))

    def grid(self, layer, x, y, rows, block=False):
        for j, row in enumerate(rows):
            for i, ref in enumerate(row.split()):
                if ref != ".":
                    self.put(layer, x + i, y + j, ref, block)

    def custom(self, layer, x, y, im_name, im, block=False):
        for (i, j), ref in custom_block(im_name, im).items():
            self.put(layer, x + i, y + j, ref, block)


# ------------------------------------------------------------------------ móveis

DESK_ITEMS = [("Mi64", "De93"), ("Mi1", "Mi58"), ("Mi74", "Mi59"), ("Mi65", "De92")]


def desk3(m, x, y, v, group):
    """Mesa de trabalho 3x2 com computador; cadeira embaixo do tile do meio."""
    m.grid("above1", x, y - 1, ["Ta0 Ta3 Ta1"])
    m.grid("furniture1", x, y, ["Ta10 Ta13 Ta11", "Ta20 Ta23 Ta21"], block=True)
    left, right = DESK_ITEMS[v % len(DESK_ITEMS)]
    m.grid("furniture3", x, y, [f"{left} Mi0 {right}"])
    m.put("furniture2", x + 1, y + 1, "Se125"); m.put("furniture2", x + 1, y + 2, "Se138")
    m.chairs.append((x + 1, y + 2, group))
    return x + 1, y + 2


def desk2(m, x, y, item, group):
    """Mesa pequena 2x2 (baia); cadeira embaixo do tile da esquerda."""
    m.grid("above1", x, y - 1, ["Ta0 Ta1"])
    m.grid("furniture1", x, y, ["Ta10 Ta11", "Ta20 Ta21"], block=True)
    m.grid("furniture3", x, y, [f"Mi1 {item}"])
    m.put("furniture2", x, y + 1, "Se125"); m.put("furniture2", x, y + 2, "Se138")
    m.chairs.append((x, y + 2, group))
    return x, y + 2


def office_desk(m, x, y, w, items, group):
    """Mesa de escritório: cadeira do titular atrás (em cima) e visitantes na frente."""
    m.grid("above1", x, y - 1, ["Ta0 " + "Ta3 " * (w - 2) + "Ta1"])
    m.grid("furniture1", x, y, ["Ta10 " + "Ta13 " * (w - 2) + "Ta11", "Ta20 " + "Ta23 " * (w - 2) + "Ta21"], block=True)
    m.grid("furniture3", x, y, [" ".join(items)])
    m.put("furniture2", x + 1, y - 1, "Se117")
    m.chairs.append((x + 1, y - 1, group))
    for gx in (x, x + w - 1):
        m.put("furniture2", gx, y + 1, "Se125"); m.put("furniture2", gx, y + 2, "Se138")
        m.chairs.append((gx, y + 2, group))
    return x + 1, y - 1


def glass_table(m, x, y, h, group):
    """Mesa de reunião de vidro 2 x h com cadeiras dos dois lados."""
    m.grid("above1", x, y - 1, ["Ta5 Ta6"])
    rows = ["Ta15 Ta17"] + ["Ta17* Ta17"] * (h - 2) + ["Ta25 Ta27"]
    m.grid("furniture1", x, y, rows, block=True)
    for j in range(h - 1):
        m.put("furniture2", x - 1, y + j, "Se119"); m.put("furniture2", x + 2, y + j, "Se120")
        m.chairs += [(x - 1, y + j, group), (x + 2, y + j, group)]


def wood_table(m, x, y, group):
    """Mesa de madeira 3x3 com cadeiras em volta."""
    m.grid("furniture1", x, y, ["Ta200 Ta201 Ta202", "Ta210 Ta211 Ta212", "Ta220 Ta221 Ta222"], block=True)
    for i in range(3):
        m.put("furniture2", x + i, y - 1, "Se117")
        m.put("above2", x + i, y + 2, "Se125"); m.put("furniture2", x + i, y + 3, "Se138")
        m.chairs += [(x + i, y - 1, group), (x + i, y + 3, group)]
    for j in range(2):
        m.put("furniture2", x - 1, y + j, "Se119"); m.put("furniture2", x + 3, y + j, "Se120")
        m.chairs += [(x - 1, y + j, group), (x + 3, y + j, group)]


def cloth_table(m, x, y, group):
    """Mesa com toalha 3x3 (refeitório) com cadeiras em volta."""
    m.grid("furniture1", x, y, ["Ta240 Ta241 Ta242", "Ta250 Ta251 Ta252", "Ta260 Ta261 Ta262"], block=True)
    m.grid("furniture3", x, y + 1, ["Mi58 . Mi59"])
    for i in range(3):
        m.put("furniture2", x + i, y - 1, "Se117")
        m.chairs.append((x + i, y - 1, group))
    for j in range(2):
        m.put("furniture2", x - 1, y + j, "Se119"); m.put("furniture2", x + 3, y + j, "Se120")
        m.chairs += [(x - 1, y + j, group), (x + 3, y + j, group)]


def round_table(m, x, y, group):
    m.put("furniture1", x, y, "Ta143", block=True)
    m.put("furniture2", x - 1, y, "Se119"); m.put("furniture2", x + 1, y, "Se120")
    m.chairs += [(x - 1, y, group), (x + 1, y, group)]


def plant(m, x, y, kind="tall"):
    """Plantas de 2 tiles (topo em cima, vaso embaixo bloqueando)."""
    top, base = {"tall": ("De78", "De90"), "snake": ("De79", "De91"), "grass": ("De75", "De87"),
                 "grass2": ("De76", "De88")}[kind]
    m.put("above1", x, y, top); m.put("furniture2", x, y + 1, base, block=True)


def palm(m, x, y):
    m.grid("above1", x, y, ["De60 De61 De62", "De72 De73 De74"])
    m.grid("furniture2", x, y + 2, ["De84 De85 De86"])
    m.blocked.add((x + 1, y + 2))


def bookshelf(m, x, y):
    """Estante 2x3 encostada na parede (topo sobre a face)."""
    m.grid("furniture2", x, y, ["OF22 OF23", "OF34 OF35", "OF46 OF47"])
    m.grid("furniture2", x, y + 2, ["OF46 OF47"], block=True)


def low_cabinet(m, x, y):
    m.grid("above1", x, y, ["OF19 OF20"]); m.grid("furniture2", x, y + 1, ["OF31 OF32"], block=True)


def window(m, x, y, curtains=True):
    m.grid("deco1", x, y, ["R775 R776", "R800 R801"])
    if curtains:
        m.grid("deco2", x, y, ["R779 R780", "R804 R805"])


def sofa(m, x, y, w=3):
    """Sofá bege virado para baixo."""
    m.grid("furniture2", x, y, ["Se0 " + "Se1 " * (w - 2) + "Se2", "Se13 " + "Se14 " * (w - 2) + "Se15"])
    for i in range(w):
        m.chairs.append((x + i, y + 1, "sofa"))


def coffee_table(m, x, y):
    m.grid("above1", x, y - 1, ["Ta45 Ta46"]); m.grid("furniture1", x, y, ["Ta55 Ta56"], block=True)


def tree(m, x, y, kind):
    """Árvore 3x3: copa acima do personagem, tronco bloqueia."""
    base = (0, 3, 6, 9, 12)[kind]
    m.grid("above1", x, y, [f"Ex{base} Ex{base + 1} Ex{base + 2}", f"Ex{base + 25} Ex{base + 26} Ex{base + 27}"])
    m.grid("furniture1", x, y + 2, [f"Ex{base + 50} Ex{base + 51} Ex{base + 52}"])
    m.blocked.add((x + 1, y + 2))


# ------------------------------------------------------------------------ construção

WALL_TILE = {0: 106, 1: 56, 4: 31, 2: 58, 8: 59, 5: 102, 10: 104, 6: 28, 12: 29, 3: 53, 9: 54,
             7: 108, 13: 158, 11: 110, 14: 160, 15: 100}


def build():
    rng = random.Random(42)
    m = Map()
    inside = lambda x, y: 0 <= x < W and 0 <= y < H

    interior = {}
    for x0, y0, x1, y1, f in ROOMS:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                interior[(x, y)] = f
    for c in DOORS:
        interior[c] = "hall"
    footprint = {(x, y) for x0, y0, x1, y1, _ in ROOMS
                 for y in range(y0 - 1, y1 + 2) for x in range(x0 - 1, x1 + 2) if inside(x, y)}
    walls = footprint - interior.keys()

    # ---- pisos e paredes
    for (x, y), f in interior.items():
        m.put("floor", x, y, FLOORS[f])
    for x, y in walls:
        mask = sum(bit for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0)))
                   if (x + dx, y + dy) in walls)
        m.put("walls", x, y, f"R{WALL_TILE[mask]}", block=True)
    for x, y in walls:
        below = (x, y + 1)
        if below in interior and below not in CORRIDOR and below not in DOORS:
            narrow = m.layers["walls"][y][x] == "R56"
            m.put("walls", x, y + 1, "R280" if narrow else "R203", block=True)
            if (x, y + 2) in interior and (x, y + 2) not in DOORS:
                m.put("walls", x, y + 2, "R305" if narrow else "R228", block=True)
        elif inside(*below) and below not in footprint:
            m.put("walls", x, y + 1, "R310", block=True)
            if inside(x, y + 2) and (x, y + 2) not in footprint:
                m.put("walls", x, y + 2, "R310", block=True)
    ext_faces = {(x, y) for y in range(H) for x in range(W) if m.layers["walls"][y][x] == "R310"}

    # ---- área externa
    water = {(x, y) for x in (0, 1) for y in range(12, H)}
    water |= {(x, y) for y in range(H) for x in range(W)
              if ((x - 11.5) / 7.2) ** 2 + ((y - 56.5) / 6.2) ** 2 <= 1}
    path = {(x, y) for x in (45, 46) for y in (0, 1)}
    outside_busy = footprint | ext_faces | water | path
    for y in range(H):
        for x in range(W):
            if (x, y) in footprint or (x, y) in ext_faces:
                continue
            if (x, y) in water:
                m.put("floor", x, y, "Ex676", block=True)
            elif (x, y) in path:
                m.put("floor", x, y, "Ex650")
            else:
                m.put("floor", x, y, "Ex628")
    for x, y in [(6, 52), (14, 54), (9, 59), (16, 58), (0, 30), (1, 44)]:
        if (x, y) in water:
            m.put("floor2", x, y, rng.choice(["Ex656", "Ex657", "Ex658", "Ex681"]))
    m.put("floor2", 12, 56, "Ex659")                                         # patinho

    used = set()
    near = {(x + dx, y + dy) for x, y in outside_busy for dx in (-1, 0, 1) for dy in (-1, 0, 1)}

    def free(cells):
        return all(inside(*c) and c not in near and c not in used for c in cells)

    trees = 0
    for _ in range(5000):
        if trees >= 34:
            break
        tx, ty = rng.randrange(0, W - 2), rng.randrange(0, H - 2)
        cells = {(tx + i, ty + j) for i in range(3) for j in range(3)}
        if free(cells):
            used |= {(x + dx, y + dy) for x, y in cells for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
            tree(m, tx, ty, rng.randrange(5)); trees += 1
    bushes = 0
    for _ in range(3000):
        if bushes >= 26:
            break
        bx, by = rng.randrange(0, W - 1), rng.randrange(0, H)
        kind = rng.choice(["bush2", "bush2b", "bush1", "rock", "rock2"])
        cells = {(bx, by), (bx + 1, by)} if kind.startswith("bush2") else {(bx, by)}
        if not free(cells):
            continue
        used |= cells; bushes += 1
        if kind == "bush2":
            m.grid("furniture1", bx, by, ["Ex450 Ex451"], block=True)
        elif kind == "bush2b":
            m.grid("furniture1", bx, by, ["Ex452 Ex453"], block=True)
        elif kind == "bush1":
            m.put("furniture1", bx, by, "Ex454", block=True)
        else:
            m.put("furniture1", bx, by, "Ex478" if kind == "rock" else "Ex480", block=True)
    decos = ["Ex506", "Ex507", "Ex508", "Ex509", "Ex575", "Ex576", "Ex577", "Ex578", "Ex579",
             "Ex581", "Ex582", "Ex583", "Ex584", "Ex600", "Ex601", "Ex602", "Ex603", "Ex605", "Ex606", "Ex607"]
    for _ in range(260):
        x, y = rng.randrange(W), rng.randrange(H)
        if (x, y) not in outside_busy and (x, y) not in used:
            m.put("floor2", x, y, rng.choice(decos)); used.add((x, y))
    for fx, fy, block in [(3, 4, ["Ex525 Ex526 Ex527", "Ex550 Ex551 Ex552"]), (76, 6, ["Ex533 Ex534", "Ex558 Ex559"]),
                          (77, 40, ["Ex528 Ex529 Ex530", "Ex553 Ex554 Ex555"]), (30, 59, ["Ex533 Ex534", "Ex558 Ex559"])]:
        cells = {(fx + i, fy + j) for j, row in enumerate(block) for i in range(len(row.split()))}
        if all(c not in outside_busy for c in cells):
            m.grid("floor2", fx, fy, block)
    for bx, by in [(18, 50), (4, 47)]:                                     # bancos perto do lago
        if free({(bx, by), (bx + 1, by)}):
            m.grid("furniture1", bx, by, ["Se143 Se144"]); used |= {(bx, by), (bx + 1, by)}

    # ---- recepção
    m.custom("deco1", 48, 3, "logo_plaque", logo_plaque(6, 2))
    m.custom("floor2", 47, 8, "logo_rug", logo_rug(7, 3))
    m.grid("above1", 48, 5, ["Ta0 Ta3 Ta3 Ta3 Ta1"])
    m.grid("furniture1", 48, 6, ["Ta10 Ta13 Ta13 Ta13 Ta11", "Ta20 Ta23 Ta23 Ta23 Ta21"], block=True)
    m.grid("furniture3", 48, 6, ["Mi74 Mi0 . Mi58 De93"])
    m.put("furniture2", 50, 5, "Se117")
    sofa(m, 44, 5)
    coffee_table(m, 44, 8)
    plant(m, 44, 9, "snake"); plant(m, 57, 5, "tall"); plant(m, 57, 9, "grass")

    # ---- auditório
    m.grid("deco1", 32, 3, ["Mi40 Mi41 Mi42", "Mi50 Mi51 Mi52"])
    m.put("furniture2", 33, 5, "OF104", block=True)
    for row in (6, 8):
        for x in list(range(26, 31)) + list(range(36, 41)):
            m.put("furniture2", x, row, "Se125"); m.put("furniture2", x, row + 1, "Se138")
    plant(m, 24, 5, "tall"); plant(m, 42, 5, "tall")
    window(m, 26, 3); window(m, 39, 3)

    # ---- salão principal
    for k, (x, y) in enumerate((x, y) for y in WORK_ROWS for x in WORK_COLS):
        cx, cy = desk3(m, x, y, k, "mesa")
        m.entries.append((f"mesa-{k + 1:02d}", cx, cy,
                          f"Salão, fileira {WORK_ROWS.index(y) + 1}, posição {WORK_COLS.index(x) + 1}"))
    for i, ty in enumerate(MEETING_ROWS):
        glass_table(m, 48, ty, 4, f"reuniao-salao-{i}")
    for wx in (25, 44):
        window(m, wx, 12)
    window(m, 47, 12, curtains=False)
    m.put("deco1", 41, 12, "Mi78")                                      # relógio
    m.grid("deco1", 30, 12, ["De77", "De89"]); m.grid("deco1", 51, 12, ["De77", "De89"])
    m.grid("furniture2", 30, 13, ["Mi46", "Mi56"]); m.blocked.add((30, 14))   # cafeteira
    m.put("furniture2", 29, 14, "Mi60", block=True)
    m.grid("furniture2", 35, 13, ["Mi27", "Mi37"]); m.blocked.add((35, 14))   # copiadora
    low_cabinet(m, 45, 13)
    plant(m, 24, 13, "tall"); plant(m, 57, 13, "tall")
    plant(m, 24, 29, "snake"); plant(m, 45, 29, "snake"); plant(m, 24, 42, "grass"); plant(m, 45, 42, "grass")
    palm(m, 55, 41)

    # ---- ala de reuniões
    for i, ty in enumerate(WING_ROWS):
        wood_table(m, 13, ty, f"reuniao-{i}")
    window(m, 9, 18); window(m, 19, 18)
    m.grid("deco1", 14, 18, ["De24 De25"])
    m.grid("furniture2", 19, 25, ["Mi33 Mi34 Mi35", "Mi43 Mi44 Mi45", "Mi53 Mi54 Mi55"])
    for i in range(3):
        m.blocked.add((19 + i, 27))
    plant(m, 8, 20, "tall"); plant(m, 22, 20, "tall"); plant(m, 8, 33, "snake"); palm(m, 8, 38)

    # ---- escritórios
    bookshelf(m, 59, 12)
    m.entries.append(("escritorio-1", *office_desk(m, 61, 15, 2, ["Mi1", "Mi64"], "escritorio-1"), "Escritório 1"))
    plant(m, 64, 13, "snake"); m.put("deco1", 63, 12, "De2")
    bookshelf(m, 66, 12)
    m.entries.append(("dra-julia", *office_desk(m, 69, 15, 2, ["Mi1", "De93"], "dra-julia"), "Escritório Dra Júlia"))
    plant(m, 72, 13, "tall"); m.grid("deco1", 70, 12, ["De0 De1"])

    # ---- lunchroom (área silenciosa)
    m.grid("furniture1", 60, 23, ["Ta95 " + "Ta96 " * 5 + "Ta97", "Ta105 " + "Ta106 " * 5 + "Ta107"], block=True)
    m.grid("furniture3", 61, 24, ["Mi57 . Mi58 . Mi59"])
    m.grid("deco1", 69, 22, ["Mi40 Mi41 Mi42", "Mi50 Mi51 Mi52"])
    cloth_table(m, 61, 27, "lunch-1"); cloth_table(m, 67, 27, "lunch-2")
    plant(m, 59, 29, "tall"); plant(m, 72, 29, "tall")
    m.put("furniture2", 72, 24, "Mi61", block=True)

    # ---- jurídico - Silvio
    bookshelf(m, 59, 33); m.grid("deco1", 63, 33, ["De24 De25"])
    m.entries.append(("juridico-silvio", *office_desk(m, 61, 37, 3, ["Mi64", "Mi0", "Mi58"], "juridico"), "Jurídico - Silvio"))
    coffee_table(m, 61, 41)
    m.grid("furniture2", 60, 43, ["Se20 Se21 Se22"]); m.chairs += [(60, 43, "sofa"), (61, 43, "sofa"), (62, 43, "sofa")]
    m.grid("furniture2", 64, 41, ["Se36", "Se49"])
    plant(m, 66, 35, "tall"); plant(m, 66, 42, "snake")

    # ---- diretoria
    m.custom("deco1", 51, 46, "logo_plaque_dir", logo_plaque(4, 2))
    bookshelf(m, 57, 46); bookshelf(m, 59, 46)
    m.entries.append(("diretoria", *office_desk(m, 55, 50, 4, ["Mi64", "Mi0", "Mi1", "De93"], "diretoria"), "Diretoria"))
    for y in range(48, 54):
        for x in range(60, 66):
            m.put("floor", x, y, "R360")
    m.grid("furniture2", 61, 48, ["Se0 Se1 Se1 Se2", "Se13 Se14 Se14 Se15"])
    coffee_table(m, 62, 51)
    m.grid("furniture2", 60, 50, ["Se59", "Se72"]); m.grid("furniture2", 65, 50, ["Se36", "Se49"])
    plant(m, 50, 48, "tall"); plant(m, 50, 53, "snake"); plant(m, 66, 53, "tall")
    m.grid("deco1", 63, 46, ["De3"]); m.grid("deco1", 61, 46, ["De26"])

    # ---- sala inferior
    for wx in (26, 29, 41, 44):
        window(m, wx, 46, curtains=False)
    for name, (bx, by), item in [("baia-1", (25, 48), "Mi65"), ("baia-2", (25, 53), "De92"),
                                 ("baia-3", (46, 48), "Mi58"), ("baia-4", (46, 53), "Mi74")]:
        cx, cy = desk2(m, bx, by, item, name)
        lado = "esquerda" if bx < 30 else "direita"
        m.entries.append((name, cx, cy, f"Sala inferior, baia {lado} de {'cima' if by < 51 else 'baixo'}"))
    for tx, ty in ((31, 49), (36, 49), (41, 49), (31, 53), (36, 53), (41, 53)):
        round_table(m, tx, ty, f"redonda-{tx}-{ty}")
    plant(m, 28, 54, "snake"); plant(m, 44, 54, "snake")

    # ---- rótulos e entrada padrão
    for text, cx, row in LABELS:
        im = label_img(text)
        start = round(cx - im.width // T / 2)
        m.custom("labels", start, row, f"label-{text}", im)
    for x, y in SPAWN:
        m.put("start", x, y, "SZ1")
    return m


# ------------------------------------------------------------------------ saída

def write_outputs(m):
    # tileset próprio
    custom_refs = sorted(_custom)
    cols = 8
    amz = new(cols * T, math.ceil(len(custom_refs) / cols) * T)
    amz_index = {}
    for k, ref in enumerate(custom_refs):
        amz.paste(_custom[ref], ((k % cols) * T, (k // cols) * T))
        amz_index[ref] = k
    amz.save(ROOT / "tilesets" / "amz.png")

    firstgid, tilesets, gid_base = 1, [], {}
    for key, name in WA_TILESETS:
        im = ts_image(key)
        gid_base[key] = firstgid
        ts = {"firstgid": firstgid, "name": name, "image": f"tilesets/wa/{name}.png",
              "imagewidth": im.width, "imageheight": im.height, "tilewidth": T, "tileheight": T,
              "tilecount": ts_count(key), "columns": ts_columns(key), "margin": 0, "spacing": 0,
              "properties": [{"name": "tilesetCopyright", "type": "string",
                              "value": "WorkAdventure - WorkAdventure specific resources license (tilesets/wa/LICENSE.assets)"}]}
        if key == "SZ":
            ts["tiles"] = [{"id": 2, "properties": [{"name": "collides", "type": "bool", "value": True}]}]
        tilesets.append(ts)
        firstgid += ts_count(key)
    gid_base["AM"] = firstgid
    tilesets.append({"firstgid": firstgid, "name": "amz", "image": "tilesets/amz.png",
                     "imagewidth": amz.width, "imageheight": amz.height, "tilewidth": T, "tileheight": T,
                     "tilecount": len(custom_refs), "columns": cols, "margin": 0, "spacing": 0})

    def gid(ref):
        if ref.startswith("AM:"):
            return gid_base["AM"] + amz_index[ref]
        flip = ref.endswith("*")
        key, local = parse(ref.rstrip("*"))
        return (gid_base[key] + local) | (FLIP if flip else 0)

    for x, y in m.blocked:
        m.put("collisions", x, y, "SZ2")

    tmj_layers, lid = [], 0

    def tile_layer(name, data, props=None):
        nonlocal lid
        lid += 1
        layer = {"id": lid, "name": name, "type": "tilelayer", "width": W, "height": H, "data": data,
                 "opacity": 1, "visible": True, "x": 0, "y": 0}
        if props:
            layer["properties"] = props
        tmj_layers.append(layer)

    objects = []
    for k, (name, x0, y0, x1, y1, props) in enumerate(AREAS, start=1):
        objects.append({"id": k, "name": name, "type": "area", "class": "area",
                        "x": x0 * T, "y": y0 * T, "width": (x1 - x0 + 1) * T, "height": (y1 - y0 + 1) * T,
                        "rotation": 0, "visible": True,
                        "properties": [{"name": key, "type": "bool" if isinstance(val, bool) else "string", "value": val}
                                       for key, val in props.items()]})
    start_gid = gid("SZ1")
    for name in LAYERS:
        if name == "floorLayer":
            lid += 1
            tmj_layers.append({"id": lid, "name": name, "type": "objectgroup", "draworder": "topdown",
                               "objects": objects, "opacity": 1, "visible": True, "x": 0, "y": 0})
            continue
        tile_layer(name, [gid(r) if r else 0 for row in m.layers[name] for r in row])
        if name == "start":   # pontos de entrada nomeados logo depois, também escondidos sob o piso
            for ename, ex, ey, _ in m.entries:
                data = [0] * (W * H); data[ey * W + ex] = start_gid
                tile_layer(ename, data, [{"name": "startLayer", "type": "bool", "value": True}])

    tmj = {
        "compressionlevel": -1, "type": "map", "version": "1.10", "tiledversion": "1.11.2",
        "orientation": "orthogonal", "renderorder": "right-down", "infinite": False,
        "width": W, "height": H, "tilewidth": T, "tileheight": T,
        "nextlayerid": lid + 1, "nextobjectid": len(objects) + 1,
        "properties": [
            {"name": "mapName", "type": "string", "value": "Escritório"},
            {"name": "mapDescription", "type": "string", "value": "Escritório virtual"},
            {"name": "mapCopyright", "type": "string",
             "value": "Tilesets: WorkAdventure (https://workadventu.re) - WorkAdventure specific resources license"},
        ],
        "layers": tmj_layers, "tilesets": tilesets,
    }
    (ROOT / "escritorio.tmj").write_text(json.dumps(tmj, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- prévias
    def tile_of(ref):
        if ref.startswith("AM:"):
            return _custom[ref]
        im = tile_image(*parse(ref.rstrip("*")))
        return ImageOps.mirror(im) if ref.endswith("*") else im

    cache = {}
    preview = Image.new("RGBA", (W * T, H * T), (0, 0, 0, 255))
    for name in LAYERS:
        if name in HIDDEN or name == "floorLayer":
            continue
        for y, row in enumerate(m.layers[name]):
            for x, ref in enumerate(row):
                if ref:
                    if ref not in cache:
                        cache[ref] = tile_of(ref)
                    preview.alpha_composite(cache[ref], (x * T, y * T))
    preview.convert("RGB").save(ROOT / "preview.png")
    preview.convert("RGB").resize((W * T * 2, H * T * 2), Image.NEAREST).save(ROOT / "preview_2x.png")

    overlay = new(W * T, H * T); d = ImageDraw.Draw(overlay)
    font, small = ImageFont.truetype("arialbd.ttf", 14), ImageFont.truetype("arialbd.ttf", 11)
    for name, x0, y0, x1, y1, props in AREAS:
        box = [x0 * T, y0 * T, (x1 + 1) * T - 1, (y1 + 1) * T - 1]
        col = (255, 140, 40) if "jitsiRoom" in props else (90, 170, 255)
        d.rectangle(box, fill=col + (60,), outline=col + (255,), width=2)
        text = f"jitsi: {props['jitsiRoom']}" if "jitsiRoom" in props else "silenciosa"
        d.text((box[0] + 4, box[1] + 3), text, font=font, fill="white", stroke_width=2, stroke_fill="black")
    for x, y in SPAWN:
        d.rectangle([x * T, y * T, x * T + T - 1, y * T + T - 1], fill=(60, 220, 120, 110), outline=(60, 220, 120, 255))
    for name, ex, ey, _ in m.entries:
        x, y = ex * T, ey * T
        d.rectangle([x, y, x + T - 1, y + T - 1], fill=(230, 60, 200, 90), outline=(230, 60, 200, 255), width=2)
        d.text((x + T // 2, y + T + 1), name, font=small, anchor="mt", fill="white", stroke_width=2, stroke_fill="black")
    areas = preview.copy(); areas.alpha_composite(overlay)
    areas.convert("RGB").save(ROOT / "preview_areas.png")

    lines = ["# Pontos de entrada", "",
             "Entrada padrão (sem `#`): **recepção** — é onde nascem os convidados.", "",
             "Para a pessoa nascer na própria mesa, use o link do mapa com `#nome-do-ponto` no final,",
             "por exemplo `.../escritorio.tmj#mesa-07`.", "",
             "| Ponto | Onde fica | Pessoa |", "|---|---|---|"]
    lines += [f"| `{name}` | {desc} | |" for name, _, _, desc in m.entries]
    (ROOT / "PONTOS_DE_ENTRADA.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"camadas: {len(tmj_layers)}  tiles próprios: {len(custom_refs)}  áreas: {len(objects)}  entradas: {len(m.entries)}")


# ------------------------------------------------------------------------ checagens

def check(m):
    todo = list(SPAWN)
    seen = set(todo)
    while todo:
        x, y = todo.pop()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= n[0] < W and 0 <= n[1] < H and n not in seen and n not in m.blocked:
                seen.add(n); todo.append(n)
    ok = True
    for x0, y0, x1, y1, _ in ROOMS:
        free = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if (x, y) not in m.blocked]
        lost = [c for c in free if c not in seen]
        if lost:
            ok = False
            print(f"  ATENÇÃO sala {x0},{y0}: {len(lost)} tiles livres sem acesso, ex.: {lost[:4]}")
    for name, ex, ey, _ in m.entries:
        if (ex, ey) not in seen:
            ok = False
            print(f"  ATENÇÃO ponto de entrada {name} sem acesso ({ex},{ey})")
    print("caminhos: todas as salas e entradas alcançáveis a partir da recepção" if ok else "caminhos: há bloqueios")

    solo = [(x, y, g) for x, y, g in m.chairs if g == "mesa" or g.startswith("baia")]
    worst = min(math.hypot(ax - bx, ay - by) for ax, ay, _ in solo for bx, by, _ in m.chairs
                if (ax, ay) != (bx, by))
    between = min(math.hypot(ax - bx, ay - by) for ax, ay, _ in solo for bx, by, _ in solo if (ax, ay) != (bx, by))
    print(f"estações: {len(solo)}  menor distância até outra cadeira: {worst:.1f} tiles ({worst * T:.0f} px)  "
          f"entre estações: {between:.1f} tiles ({between * T:.0f} px)")


if __name__ == "__main__":
    mp = build()
    write_outputs(mp)
    check(mp)
