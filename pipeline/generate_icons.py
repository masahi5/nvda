"""PWA アイコン生成（一度だけ実行すればよい）。

    uv run --with pillow python generate_icons.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ICONS = Path(__file__).resolve().parent.parent / "icons"
GREEN = (118, 185, 0)
DARK = (11, 14, 17)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make(size: int, maskable: bool, name: str) -> None:
    img = Image.new("RGBA", (size, size), DARK + (255,))
    d = ImageDraw.Draw(img)
    # 角丸の緑パネル（maskable は余白小さめ＝フルブリード寄り）
    pad = int(size * (0.06 if maskable else 0.1))
    radius = int(size * 0.22)
    d.rounded_rectangle([pad, pad, size - pad, size - pad], radius=radius, fill=GREEN)
    # テキスト "NV"
    font = _font(int(size * 0.42))
    text = "NV"
    box = d.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    d.text(((size - tw) / 2 - box[0], (size - th) / 2 - box[1]), text, font=font, fill=DARK)
    ICONS.mkdir(parents=True, exist_ok=True)
    img.save(ICONS / name)
    print("[ok]", ICONS / name)


if __name__ == "__main__":
    make(192, False, "icon-192.png")
    make(512, False, "icon-512.png")
    make(512, True, "icon-maskable-512.png")
