"""Acesso aos tilesets oficiais do WorkAdventure (tilesets/wa) e uma cena simples para testes."""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
T = 32

# ordem = ordem dos tilesets no .tmj (define o firstgid)
WA_TILESETS = [
    ("SZ", "WA_Special_Zones"), ("De", "WA_Decoration"), ("Mi", "WA_Miscellaneous"),
    ("OF", "WA_Other_Furniture"), ("R", "WA_Room_Builder"), ("Se", "WA_Seats"),
    ("Ta", "WA_Tables"), ("Lo", "WA_Logo_Long"), ("Ex", "WA_Exterior"),
]

_images = {}


def ts_image(key):
    if key not in _images:
        name = dict(WA_TILESETS)[key]
        _images[key] = Image.open(ROOT / "tilesets" / "wa" / f"{name}.png").convert("RGBA")
    return _images[key]


def ts_columns(key):
    return ts_image(key).width // T


def ts_count(key):
    im = ts_image(key)
    return (im.width // T) * (im.height // T)


def tile_image(key, local):
    im = ts_image(key)
    cols = im.width // T
    x, y = (local % cols) * T, (local // cols) * T
    return im.crop((x, y, x + T, y + T))


def parse(ref):
    """'Ta12' -> ('Ta', 12)"""
    k = ref.rstrip("0123456789")
    return k, int(ref[len(k):])


class Scene:
    """Grade com camadas nomeadas; cada célula guarda uma referência 'Ta12'."""

    def __init__(self, w, h, layers):
        self.w, self.h = w, h
        self.layers = {n: [[None] * w for _ in range(h)] for n in layers}

    def put(self, layer, x, y, ref):
        if ref and 0 <= x < self.w and 0 <= y < self.h:
            self.layers[layer][y][x] = ref

    def grid(self, layer, x, y, rows):
        """rows: lista de strings 'Ta0 Ta3 Ta1' (use '.' para vazio)."""
        for j, row in enumerate(rows):
            for i, ref in enumerate(row.split()):
                if ref != ".":
                    self.put(layer, x + i, y + j, ref)

    def render(self, order, custom=None):
        out = Image.new("RGBA", (self.w * T, self.h * T), (0, 0, 0, 255))
        for name in order:
            for y, row in enumerate(self.layers[name]):
                for x, ref in enumerate(row):
                    if ref:
                        tile = custom[ref] if custom and ref in custom else tile_image(*parse(ref))
                        out.alpha_composite(tile, (x * T, y * T))
        return out
