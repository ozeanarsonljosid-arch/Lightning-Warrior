"""生成原创子弹 / 爆炸素材（Pillow + numpy）。可改参数后重跑。

输出到 ../figure/：
  bullet_player.png    玩家子弹（冷白→青，纵向等离子弹）
  bullet_boss.png      Boss 子弹（暗紫核心 + 洋红光环的“魂球”）
  explosion_0..7.png   爆炸 8 帧，96x96，Alpha
  _preview.png         合成预览图（只用于查看，不进游戏）
"""
from pathlib import Path
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figure"
SS = 4          # 超采样倍数：先画大图再缩小，边缘更干净


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def lerp3(a, b, t):
    return a * (1 - t) + b * t


def to_image(rgba):
    return Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA")


def noise_field(S, rnd, scale=2.0, octaves=3):
    """平滑的二维噪声（几个正弦叠加），用来扰乱火球边缘。"""
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / S
    field = np.zeros((S, S), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        fx = rnd.uniform(1.0, 2.2) * scale * (2 ** o)
        fy = rnd.uniform(1.0, 2.2) * scale * (2 ** o)
        ph = rnd.uniform(0, 2 * math.pi)
        field += amp * np.sin(2 * math.pi * (fx * xx + fy * yy) + ph)
        total += amp
        amp *= 0.55
    return (field / total + 1) / 2


def player_bullet(w=24, h=64):
    W, H = w * SS, h * SS
    yy, xx = np.mgrid[0:H, 0:W]
    cx = (W - 1) / 2
    u = (xx - cx) / (W / 2)              # 横向 -1..1
    t = yy / (H - 1)                     # 纵向 0 弹头 1 弹尾
    au = np.abs(u)

    # 轮廓：向上收成尖，中段最宽
    f = (t ** 0.52) * (1 - 0.45 * t) * 0.94
    shape = smoothstep(0.0, 0.13, f - au)
    k = np.clip(au / np.maximum(f, 1e-6), 0, 1)

    # 颜色：白热 → 青 → 外缘洋红
    hot = np.array([1.00, 1.00, 1.00])
    mid = np.array([0.34, 0.88, 1.00])
    edge = np.array([0.78, 0.34, 1.00])
    col = lerp3(hot, mid, smoothstep(0.04, 0.60, k)[..., None])
    col = lerp3(col, edge, smoothstep(0.84, 1.00, k)[..., None])

    # 轴线亮芯
    axis = np.exp(-(u / 0.15) ** 2) * shape
    col = col + (np.array([1.0, 1.0, 1.0]) - col) * (axis * 0.8)[..., None]

    # 尾部渐隐，避免一刀切的平口
    tail = 1 - smoothstep(0.70, 1.0, t)
    a = shape * tail

    # 外发光
    glow_src = np.clip(f - au, 0, 1) * tail ** 0.8
    gi = Image.fromarray((glow_src * 255).astype(np.uint8), "L")
    g = np.asarray(gi.filter(ImageFilter.GaussianBlur(W * 0.22)), np.float32) / 255
    halo = np.array([0.22, 0.70, 1.00]) * g[..., None]

    rgb = col * a[..., None] + halo * 1.05
    alpha = np.clip(a + g * 1.15, 0, 1)
    return to_image(np.dstack([np.clip(rgb, 0, 1), alpha])).resize((w, h), Image.LANCZOS)


def boss_bullet(size=32):
    S = size * SS
    yy, xx = np.mgrid[0:S, 0:S]
    c = (S - 1) / 2
    r = np.hypot(xx - c, yy - c) / (S / 2)

    body = 1 - smoothstep(0.42, 0.76, r)         # 球体，留出外围光晕空间
    core = np.exp(-((r / 0.34) ** 2))
    rim = np.exp(-((r - 0.64) / 0.10) ** 2)      # 软环
    halo = np.exp(-((r / 0.88) ** 2))            # 外光

    col = np.zeros((S, S, 3), np.float32)
    col += np.array([0.26, 0.04, 0.38]) * body[..., None]
    col += np.array([0.52, 0.16, 0.92]) * (halo * 0.55)[..., None]
    col += np.array([1.00, 0.45, 1.00]) * (rim * 0.95)[..., None]
    col -= np.array([0.12, 0.03, 0.16]) * core[..., None]     # 中心压暗

    # 左上高光
    spec = np.exp(-(((xx - c + S * 0.14) ** 2 + (yy - c + S * 0.16) ** 2) / (S * 0.11) ** 2))
    col += np.array([1.0, 0.88, 1.0]) * (spec * 0.45)[..., None]

    alpha = np.clip(body * 0.90 + rim * 0.70 + halo * 0.30, 0, 1)
    return to_image(np.dstack([np.clip(col, 0, 1), alpha])).resize((size, size), Image.LANCZOS)


def explosion_frame(p, size, rnd):
    """p: 0 起爆 → 1 消散。用噪声扰动半径，得到气团状轮廓。"""
    S = size * SS
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    c = (S - 1) / 2
    rad = np.hypot(xx - c, yy - c) / (S * 0.5)

    R = 0.26 + 0.66 * p
    n1 = noise_field(S, rnd, 1.5)
    n2 = noise_field(S, rnd, 3.0)
    warp = 1 + 0.55 * (n1 - 0.5) * 2               # 0.45..1.55，边缘不规则

    body = smoothstep(1.0, 0.26, rad / (R * warp)) * (0.55 + 0.45 * n2)
    hotness = max(0.0, 1 - 1.35 * p) ** 1.25
    fade = 1 - 0.62 * p

    orange = np.array([1.00, 0.42, 0.12], np.float32)
    white = np.array([1.00, 0.98, 0.88], np.float32)
    glow_core = np.clip(body * 1.7, 0, 1) ** 2 * hotness
    col = orange * body[..., None] + white * glow_core[..., None] * 1.15
    alpha = body * 0.98 * fade

    fire = Image.fromarray(
        np.dstack([np.clip(col, 0, 1) * 255, np.clip(alpha, 0, 1) * 255]).astype(np.uint8), "RGBA"
    )
    fire = fire.filter(ImageFilter.GaussianBlur(S * 0.008))

    # 后层烟：只在后半段出现，让火球散开
    smoke_img = None
    if p > 0.28:
        smoke_a = 0.60 * smoothstep(0.28, 1.0, p) * smoothstep(1.05, 0.30, rad / (R * 1.25 * warp))
        smoke_col = np.array([0.14, 0.11, 0.12], np.float32)
        smoke_img = Image.fromarray(
            np.dstack([np.full((S, S), smoke_col[0] * 255), np.full((S, S), smoke_col[1] * 255),
                       np.full((S, S), smoke_col[2] * 255), np.clip(smoke_a, 0, 1) * 255]).astype(np.uint8),
            "RGBA",
        ).filter(ImageFilter.GaussianBlur(S * 0.03))

    glow = fire.filter(ImageFilter.GaussianBlur(S * 0.05))
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    if smoke_img is not None:
        out.alpha_composite(smoke_img)
    out.alpha_composite(glow)
    out.alpha_composite(fire)

    # 火花：独立绘制，保持锐利
    sparks = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sparks)
    for _ in range(52):
        ang = rnd.uniform(0, 2 * math.pi)
        dist = R * S * 0.5 * rnd.uniform(0.70, 1.35)
        length = R * S * 0.5 * rnd.uniform(0.04, 0.16)
        a = int(250 * (1 - p) ** 1.1 * rnd.uniform(0.45, 1.0))
        if a <= 4:
            continue
        x1, y1 = c + math.cos(ang) * dist, c + math.sin(ang) * dist
        x2, y2 = c + math.cos(ang) * (dist + length), c + math.sin(ang) * (dist + length)
        sd.line([x1, y1, x2, y2], fill=(255, int(232 - 55 * p), int(175 - 110 * p), a),
                width=max(1, int(4 * (1 - p) + 1)))

    # 冲击波环：模糊后很淡，避免像齿轮
    if p < 0.8:
        ring = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        rd = ImageDraw.Draw(ring)
        rr = R * S * 0.5 * 1.22
        rd.ellipse([c - rr, c - rr, c + rr, c + rr],
                   outline=(255, 198, 140, int(95 * (1 - p))), width=max(2, int(8 * (1 - p))))
        out.alpha_composite(ring.filter(ImageFilter.GaussianBlur(S * 0.012)))

    out.alpha_composite(sparks)
    return out.resize((size, size), Image.LANCZOS)


def preview(bullets, frames):
    """把素材拼到深色背景上，方便肉眼检查配色和可读性。"""
    W, H = 760, 340
    bg = Image.new("RGBA", (W, H), (24, 26, 36, 255))
    d = ImageDraw.Draw(bg)

    pb = bullets["player"].resize((bullets["player"].width * 3,
                                   bullets["player"].height * 3), Image.LANCZOS)
    bb = bullets["boss"].resize((bullets["boss"].width * 3,
                                 bullets["boss"].height * 3), Image.LANCZOS)
    bg.alpha_composite(pb, (40, 60))
    bg.alpha_composite(bb, (150, 110))

    # 原船图做配色对照
    for i, name in enumerate(("Player.png", "Boss.png")):
        ship = Image.open(FIG / name).convert("RGBA")
        ship.thumbnail((150, 110), Image.LANCZOS)
        bg.alpha_composite(ship, (270 + i * 180, 50))

    x, y = 40, 215
    for f in frames:
        bg.alpha_composite(f, (x, y))
        x += f.width + 6

    d.text((40, 14), "player bullet / boss bullet / explosion 8 frames", fill=(205, 215, 235, 255))
    return bg


def main():
    FIG.mkdir(exist_ok=True)
    player = player_bullet()
    boss = boss_bullet()
    player.save(FIG / "bullet_player.png")
    boss.save(FIG / "bullet_boss.png")

    rnd = random.Random(20261121)
    frames = []
    for i in range(8):
        p = i / 7
        f = explosion_frame(p, 96, rnd)
        f.save(FIG / f"explosion_{i}.png")
        frames.append(f)

    preview({"player": player, "boss": boss}, frames).save(FIG / "_preview.png")
    print("player bullet:", player.size)
    print("boss bullet  :", boss.size)
    print("frames       :", frames[0].size, "x", len(frames))


if __name__ == "__main__":
    main()
