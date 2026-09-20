"""CookMateのロゴ画像(assets/icon.png)を作るスクリプト。

スマホのホーム画面に追加したときのアイコンとして使う。
一度作ればよいファイルなので、実行するのはデザインを変えたいときだけでよい。
"""

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 512
OUT_PATH = Path(__file__).parent / "assets" / "icon.png"

BG_TOP = (255, 138, 91)  # 暖色系グラデーションの上側
BG_BOTTOM = (255, 107, 53)  # CookMateのテーマカラー
PAN_COLOR = (255, 253, 247)
EGG_WHITE = (255, 253, 247)
EGG_YOLK = (255, 196, 61)


def make_icon() -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), BG_BOTTOM)
    draw = ImageDraw.Draw(img)

    # 背景のグラデーション(上から下へ)
    for y in range(SIZE):
        t = y / SIZE
        r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
        draw.line([(0, y), (SIZE, y)], fill=(r, g, b))

    # 角を丸くする(スマホのアイコンらしい見た目に)
    mask = Image.new("L", (SIZE, SIZE), 0)
    mask_draw = ImageDraw.Draw(mask)
    radius = int(SIZE * 0.22)
    mask_draw.rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=radius, fill=255)

    # フライパン(取っ手+丸いフライパン本体)
    cx, cy = int(SIZE * 0.58), int(SIZE * 0.54)
    pan_r = int(SIZE * 0.24)
    draw.ellipse(
        [cx - pan_r, cy - pan_r, cx + pan_r, cy + pan_r],
        fill=PAN_COLOR,
    )
    handle_w = int(SIZE * 0.10)
    handle_len = int(SIZE * 0.28)
    handle_y0 = cy - handle_w // 2
    handle_y1 = cy + handle_w // 2
    draw.rounded_rectangle(
        [cx - pan_r - handle_len, handle_y0, cx - pan_r + 10, handle_y1],
        radius=handle_w // 2,
        fill=PAN_COLOR,
    )

    # 目玉焼き(白身+黄身)
    egg_r = int(pan_r * 0.72)
    draw.ellipse(
        [cx - egg_r, cy - egg_r, cx + egg_r, cy + egg_r],
        fill=EGG_WHITE,
        outline=(240, 220, 200),
        width=3,
    )
    yolk_r = int(egg_r * 0.42)
    yolk_cx, yolk_cy = cx - int(egg_r * 0.12), cy - int(egg_r * 0.08)
    draw.ellipse(
        [yolk_cx - yolk_r, yolk_cy - yolk_r, yolk_cx + yolk_r, yolk_cy + yolk_r],
        fill=EGG_YOLK,
    )

    result = Image.new("RGBA", (SIZE, SIZE))
    result.paste(img, (0, 0), mask=mask)
    return result


if __name__ == "__main__":
    icon = make_icon()
    OUT_PATH.parent.mkdir(exist_ok=True)
    icon.save(OUT_PATH)
    print("作成しました:", OUT_PATH)
