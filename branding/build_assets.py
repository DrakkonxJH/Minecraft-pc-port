#!/usr/bin/env python3
"""Gera todos os assets de marca do MineDrakk a partir das artes em branding/.

O modelo de imagem devolve PNG sem canal alfa: a transparencia vem desenhada
como um padrao xadrez. Este script detecta e remove esse xadrez, recorta a arte
e exporta nas densidades que o Android exige.

Uso: python3 branding/build_assets.py
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "app_pojavlauncher", "src", "main", "res")
ASSETS = os.path.join(HERE, "..", "app_pojavlauncher", "src", "main", "assets")

# Densidades do launcher icon (baseline 48dp)
MIPMAP = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
# Foreground do adaptive icon: 108dp de canvas
MIPMAP_FG = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}

BRAND_GREEN = (46, 204, 113)
BG_DARK = (20, 24, 20)


def is_checkerboard_pixel(px):
    """O xadrez de transparencia e cinza/branco dessaturado."""
    r, g, b = px[:3]
    if abs(r - g) > 12 or abs(g - b) > 12 or abs(r - b) > 12:
        return False          # tem cor -> e arte
    return r > 96             # cinza claro ou branco


def strip_checkerboard(img, tol=26):
    """Remove o padrao xadrez, tornando-o transparente.

    Faz flood fill a partir das bordas para nao apagar cinzas legitimos
    que estejam dentro da arte.
    """
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()

    from collections import deque
    seen = [[False] * h for _ in range(w)]
    q = deque()

    for x in range(w):
        for y in (0, h - 1):
            if is_checkerboard_pixel(px[x, y]):
                q.append((x, y)); seen[x][y] = True
    for y in range(h):
        for x in (0, w - 1):
            if is_checkerboard_pixel(px[x, y]) and not seen[x][y]:
                q.append((x, y)); seen[x][y] = True

    while q:
        x, y = q.popleft()
        px[x, y] = (0, 0, 0, 0)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[nx][ny]:
                if is_checkerboard_pixel(px[nx, ny]):
                    seen[nx][ny] = True
                    q.append((nx, ny))
    return img


def autocrop(img, pad_ratio=0.0):
    bbox = img.getbbox()
    if not bbox:
        return img
    img = img.crop(bbox)
    if pad_ratio:
        w, h = img.size
        p = int(max(w, h) * pad_ratio)
        out = Image.new("RGBA", (w + 2 * p, h + 2 * p), (0, 0, 0, 0))
        out.paste(img, (p, p))
        img = out
    return img


def fit_square(img, size, scale=1.0):
    """Encaixa a arte centralizada num canvas quadrado transparente."""
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    target = int(size * scale)
    a = img.copy()
    a.thumbnail((target, target), Image.LANCZOS)
    canvas.paste(a, ((size - a.width) // 2, (size - a.height) // 2), a)
    return canvas


def round_corners(img, radius_ratio=0.22):
    from PIL import ImageDraw
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w, h], int(w * radius_ratio), fill=255)
    out = img.copy().convert("RGBA")
    out.putalpha(mask)
    return out


def save(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "PNG", optimize=True)
    print(f"  {os.path.relpath(path, os.path.join(HERE, '..'))}  {img.size[0]}x{img.size[1]}")


def main():
    icon_src = Image.open(os.path.join(HERE, "logo_icon.png")).convert("RGBA")
    fg_src = strip_checkerboard(Image.open(os.path.join(HERE, "logo_foreground.png")))
    wm_src = Image.open(os.path.join(HERE, "logo_wordmark_clean.png")).convert("RGBA")

    fg_art = autocrop(fg_src)
    wm_art = autocrop(wm_src)

    print("Adaptive icon: background solido")
    for d, size in MIPMAP_FG.items():
        bg = Image.new("RGBA", (size, size), BG_DARK + (255,))
        save(bg, os.path.join(RES, f"mipmap-{d}", "ic_launcher_background.png"))

    print("Adaptive icon: foreground (dragao)")
    for d, size in MIPMAP_FG.items():
        # 0.62 mantem a arte dentro da safe zone de 66dp do adaptive icon
        save(fit_square(fg_art, size, 0.62),
             os.path.join(RES, f"mipmap-{d}", "ic_launcher_foreground.png"))

    print("Icone legado (Android < 8) e round")
    for d, size in MIPMAP.items():
        base = Image.new("RGBA", (size, size), BG_DARK + (255,))
        art = fit_square(fg_art, size, 0.70)
        base.alpha_composite(art)
        save(round_corners(base, 0.22), os.path.join(RES, f"mipmap-{d}", "ic_launcher.png"))
        rnd = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        circ = Image.new("RGBA", (size, size), BG_DARK + (255,))
        circ.alpha_composite(art)
        save(round_corners(circ, 0.5), os.path.join(RES, f"mipmap-{d}", "ic_launcher_round.png"))

    print("Icone monocromatico (Material You)")
    for d, size in MIPMAP_FG.items():
        mono = fit_square(fg_art, size, 0.62)
        # achata para branco solido preservando a silhueta
        flat = Image.new("RGBA", mono.size, (255, 255, 255, 0))
        flat.putalpha(mono.getchannel("A"))
        save(flat, os.path.join(RES, f"mipmap-{d}", "ic_launcher_monochrome.png"))

    print("Wordmark da tela inicial")
    for d, w in {"mdpi": 240, "hdpi": 360, "xhdpi": 480, "xxhdpi": 720, "xxxhdpi": 960}.items():
        a = wm_art.copy()
        a.thumbnail((w, w), Image.LANCZOS)
        save(a, os.path.join(RES, f"drawable-{d}", "ic_minedrakk_wordmark.png"))

    print("Assets (tela de about / splash)")
    icon_512 = icon_src.copy(); icon_512.thumbnail((512, 512), Image.LANCZOS)
    save(icon_512, os.path.join(ASSETS, "minedrakk.png"))

    print("\nConcluido.")


if __name__ == "__main__":
    main()
