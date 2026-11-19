"""Generate animated 4x4 Bayer-dithered meadow hero SVGs for GitHub README.

Faithfully ports the scene geometry, palettes, character night-variant baking,
4x4 Bayer dithering, and atmospheric animations from DitherMeadowScene.tsx.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DEFAULT_SPRITE = Path(r"C:\PortfolioAli\public\meadow\character-asleep.png")

BW = 282
BH = 100
SCALE = 3
BANNER_W = BW * SCALE  # 846
BANNER_H = BH * SCALE  # 300
SVG_W = 848
SVG_H = 518  # 452 + (300 - 234)

NUM_FRAMES = 12
FRAME_DURATION = 0.4
LOOP_DURATION = round(NUM_FRAMES * FRAME_DURATION, 2)  # 4.8s

SUPERSAMPLE = 4
BAYER_SPREAD = 46.0

# 4x4 Bayer threshold matrix centered in [-0.5, +0.5)
BAYER_4X4 = (
    np.array(
        [
            [0, 8, 2, 10],
            [12, 4, 14, 6],
            [3, 11, 1, 9],
            [15, 7, 13, 5],
        ],
        dtype=np.float32,
    )
    / 16.0
    - 0.5
)

LIGHT_PALETTE = [
    (245, 244, 241),  # #f5f4f1 exact paper bg
    (233, 206, 178),  # #e9ceb2 warm skin / sunlight
    (154, 168, 128),  # #9aa880 sunlit sage meadow & canopy
    (92, 105, 67),    # #5c6943 muted olive sweater & foliage
    (38, 37, 35),     # #262523 charcoal ink: hair, glasses, bark
]

DARK_PALETTE = [
    (26, 25, 23),     # #1a1917 exact charcoal page bg
    (14, 14, 13),     # #0e0e0d obsidian glasses, eyes, hair core
    (52, 60, 46),     # #343c2e moonlit moss / hill / night mist
    (108, 124, 90),   # #6c7c5a moonlit sage sweater & grass rim
    (218, 186, 152),  # #daba98 warm moonlit skin & firefly halo
    (242, 235, 224),  # #f2ebe0 warm cream stripes, moon, stars, socks
]


def rgb_hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def js_hash(n: int) -> float:
    """Port of the deterministic 32-bit hash() from DitherMeadowScene.tsx."""
    x = (n & 0xFFFFFFFF) ^ 0x9E3779B9
    x = ((x ^ (x >> 16)) * 0x85EBCA6B) & 0xFFFFFFFF
    x = ((x ^ (x >> 13)) * 0xC2B2AE35) & 0xFFFFFFFF
    x = (x ^ (x >> 16)) & 0xFFFFFFFF
    return x / 4294967296.0


def build_seeds() -> dict[str, list[dict]]:
    stars = [
        {
            "u": js_hash(i * 17 + 1),
            "v": 0.06 + js_hash(i * 31 + 2) * 0.44,
            "phase": js_hash(i * 43 + 3) * math.pi * 2.0,
            "big": js_hash(i * 59 + 4) > 0.8,
        }
        for i in range(34)
    ]

    grass = []
    for i in range(145):
        is_flower = i % 11 == 0
        is_fg = i % 5 == 0
        grass.append(
            {
                "u": js_hash(i * 73 + 5),
                "h": 4.0 + js_hash(i * 89 + 6) * 8.0,
                "lean": (js_hash(i * 97 + 7) - 0.5) * 3.5,
                "phase": js_hash(i * 101 + 8) * math.pi * 2.0,
                "thick": 1.5 if js_hash(i * 113 + 9) > 0.72 else 1.0,
                "fg": is_fg,
                "flower": is_flower,
            }
        )

    fireflies = [
        {
            "u": 0.06 + js_hash(i * 137 + 11) * 0.88,
            "v": js_hash(i * 149 + 12),
            "phase": js_hash(i * 163 + 13) * math.pi * 2.0,
            "amp_x": 1.5 + js_hash(i * 179 + 14) * 2.0,
            "amp_y": 1.2 + js_hash(i * 191 + 15) * 2.0,
        }
        for i in range(10)
    ]

    return {"stars": stars, "grass": grass, "fireflies": fireflies}


def bake_sprite_variants(sprite_path: Path) -> tuple[Image.Image, Image.Image]:
    """Port bakeSpriteVariants() for day and night character sprites."""
    day_img = Image.open(sprite_path).convert("RGBA")
    arr = np.array(day_img, dtype=np.float32)

    a = arr[:, :, 3]
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]

    lum = 0.299 * r + 0.587 * g + 0.114 * b
    visible = a >= 8.0

    m_dark = visible & (lum < 62.0)
    m_cream = visible & (~m_dark) & (r > 210.0) & (g > 205.0) & (b > 190.0)
    m_skin = visible & (~m_dark) & (~m_cream) & (r > 215.0) & ((r - b) > 35.0)
    m_olive = (
        visible
        & (~m_dark)
        & (~m_cream)
        & (~m_skin)
        & (g >= r - 8.0)
        & (g > b + 12.0)
        & (r < 150.0)
    )
    m_trousers = visible & (~m_dark) & (~m_cream) & (~m_skin) & (~m_olive)

    night_arr = arr.copy()

    # Hair, glasses, eyes, mouth -> deep obsidian
    night_arr[m_dark, 0] = np.round(r[m_dark] * 0.45 + 6.0)
    night_arr[m_dark, 1] = np.round(g[m_dark] * 0.45 + 6.0)
    night_arr[m_dark, 2] = np.round(b[m_dark] * 0.45 + 5.0)

    # Cream sweater stripes & socks -> moonlit cream
    night_arr[m_cream, 0] = np.round(r[m_cream] * 0.92)
    night_arr[m_cream, 1] = np.round(g[m_cream] * 0.91)
    night_arr[m_cream, 2] = np.round(b[m_cream] * 0.89)

    # Skin -> moonlit warm peach
    night_arr[m_skin, 0] = np.round(r[m_skin] * 0.87)
    night_arr[m_skin, 1] = np.round(g[m_skin] * 0.88)
    night_arr[m_skin, 2] = np.round(b[m_skin] * 0.86)

    # Olive stripes -> moonlit sage
    night_arr[m_olive, 0] = np.round(np.clip(r[m_olive] * 1.04, 0, 255))
    night_arr[m_olive, 1] = np.round(np.clip(g[m_olive] * 1.18, 0, 255))
    night_arr[m_olive, 2] = np.round(np.clip(b[m_olive] * 1.16, 0, 255))

    # Dark trousers -> moonlit charcoal slate
    night_arr[m_trousers, 0] = np.round(r[m_trousers] * 0.88)
    night_arr[m_trousers, 1] = np.round(g[m_trousers] * 0.92)
    night_arr[m_trousers, 2] = np.round(b[m_trousers] * 0.94)

    night_img = Image.fromarray(np.clip(night_arr, 0, 255).astype(np.uint8), "RGBA")
    return day_img, night_img


def quad_bezier_pts(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    steps: int = 16,
) -> list[tuple[float, float]]:
    pts = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1.0 - t
        x = mt * mt * p0[0] + 2.0 * mt * t * p1[0] + t * t * p2[0]
        y = mt * mt * p0[1] + 2.0 * mt * t * p1[1] + t * t * p2[1]
        pts.append((x, y))
    return pts


def draw_thick_curve(
    draw: ImageDraw.ImageDraw,
    pts: list[tuple[float, float]],
    width: float,
    color: tuple[int, int, int, int],
) -> None:
    w = max(1, int(round(width)))
    draw.line(pts, fill=color, width=w, joint="curve")
    r = width * 0.5
    if r >= 0.8:
        for px, py in (pts[0], pts[-1]):
            draw.ellipse([px - r, py - r, px + r, py + r], fill=color)


def composite_rgba_layer(canvas: np.ndarray, overlay_hi: Image.Image) -> None:
    """Premultiplied box-downsample from supersampled RGBA overlay onto float32 RGB canvas."""
    arr = np.array(overlay_hi, dtype=np.float32) / 255.0
    a = arr[:, :, 3:4]
    premul = arr[:, :, :3] * a
    combined = np.concatenate([premul, a], axis=2)
    down = combined.reshape(BH, SUPERSAMPLE, BW, SUPERSAMPLE, 4).mean(axis=(1, 3))
    fg_rgb = down[:, :, :3] * 255.0
    fg_a = down[:, :, 3:4]
    canvas[:] = fg_rgb + canvas * (1.0 - fg_a)


def blend_radial_gradient(
    canvas: np.ndarray,
    cx: float,
    cy: float,
    r0: float,
    r1: float,
    stops: list[tuple[float, tuple[int, int, int], float]],
    y_clip: float | None = None,
) -> None:
    """Alpha-over radial gradient directly at logical canvas resolution."""
    yy, xx = np.mgrid[0:BH, 0:BW].astype(np.float32)
    xx += 0.5
    yy += 0.5
    dist = np.hypot(xx - cx, yy - cy)
    t = np.clip((dist - r0) / max(1e-5, r1 - r0), 0.0, 1.0)

    stop_pos = np.array([s[0] for s in stops], dtype=np.float32)
    stop_r = np.array([s[1][0] for s in stops], dtype=np.float32)
    stop_g = np.array([s[1][1] for s in stops], dtype=np.float32)
    stop_b = np.array([s[1][2] for s in stops], dtype=np.float32)
    stop_a = np.array([s[2] for s in stops], dtype=np.float32)

    alpha = np.interp(t, stop_pos, stop_a)
    alpha[dist >= r1] = 0.0
    if y_clip is not None:
        alpha[yy >= y_clip] = 0.0

    rr = np.interp(t, stop_pos, stop_r)
    gg = np.interp(t, stop_pos, stop_g)
    bb = np.interp(t, stop_pos, stop_b)

    mask = alpha > 0.0
    if not np.any(mask):
        return
    a = alpha[mask, None]
    rgb = np.stack([rr[mask], gg[mask], bb[mask]], axis=-1)
    canvas[mask] = rgb * a + canvas[mask] * (1.0 - a)


def compute_layout() -> dict[str, float]:
    ground_y = 85.0
    hill_bottom_y = 99.0
    char_size = 66.0
    char_x = BW * 0.64
    char_base_y = ground_y + char_size * 0.04
    tree_x = char_x + char_size * 0.43
    canopy_cx = tree_x - char_size * 0.22
    canopy_cy = 15.0
    canopy_rx = 56.0
    canopy_ry = 22.0
    return {
        "ground_y": ground_y,
        "hill_bottom_y": hill_bottom_y,
        "char_size": char_size,
        "char_x": char_x,
        "char_base_y": char_base_y,
        "tree_x": tree_x,
        "canopy_cx": canopy_cx,
        "canopy_cy": canopy_cy,
        "canopy_rx": canopy_rx,
        "canopy_ry": canopy_ry,
    }


def knoll_profile(x: np.ndarray | float, layout: dict[str, float]) -> np.ndarray | float:
    dx = (x - (layout["char_x"] + layout["char_size"] * 0.12)) / (BW * 0.36)
    mound = np.exp(-dx * dx * 1.4) * (BH * 0.024)
    slope = np.sin((x / BW) * math.pi * 1.6) * (BH * 0.012)
    return layout["ground_y"] - mound + slope


def prepare_sprite(sprite_img: Image.Image, target_px: int) -> Image.Image:
    """Resize straight RGBA sprite smoothly for clean rotation/breathing."""
    return sprite_img.resize((target_px, target_px), Image.Resampling.LANCZOS)


def draw_sprite_onto_hi(
    hi_canvas: Image.Image,
    sprite_img: Image.Image,
    cx_hi: float,
    base_y_hi: float,
    size_hi: float,
    scale_x: float,
    scale_y: float,
    angle_rad: float,
) -> None:
    """Transform straight RGBA sprite with breathing scale & gentle sway onto supersampled RGBA."""
    sw = max(1, int(round(size_hi * scale_x)))
    sh = max(1, int(round(size_hi * scale_y)))
    scaled = sprite_img.resize((sw, sh), Image.Resampling.BILINEAR)

    seat_ratio = 496.0 / 512.0
    anchor_dy = (seat_ratio - 0.5) * sh
    deg = -math.degrees(angle_rad)

    pad = 16
    cw = sw + pad * 2
    ch = sh + pad * 2
    padded = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    padded.paste(scaled, (pad, pad))

    rotated = padded.rotate(
        deg, resample=Image.Resampling.BILINEAR, center=(cw * 0.5, ch * 0.5 + anchor_dy)
    )

    paste_x = int(round(cx_hi - cw * 0.5))
    paste_y = int(round(base_y_hi - (ch * 0.5 + anchor_dy)))
    hi_canvas.paste(rotated, (paste_x, paste_y), rotated)


def bayer_dither(
    canvas_rgb: np.ndarray, palette: list[tuple[int, int, int]], light: bool
) -> np.ndarray:
    """Exact port of DitherMeadowScene.tsx 4x4 Bayer multi-tone dither pass."""
    bg = np.array(palette[0], dtype=np.float32)
    r0 = canvas_rgb[:, :, 0]
    g0 = canvas_rgb[:, :, 1]
    b0 = canvas_rgb[:, :, 2]

    untouched = (
        (np.abs(r0 - bg[0]) <= 1.0)
        & (np.abs(g0 - bg[1]) <= 1.0)
        & (np.abs(b0 - bg[2]) <= 1.0)
    )

    bayer_tiled = np.tile(BAYER_4X4, (BH // 4 + 1, BW // 4 + 1))[:BH, :BW]
    d = bayer_tiled * BAYER_SPREAD

    r = r0 + d
    g = g0 + d
    b = b0 + d

    pal_arr = np.array(palette, dtype=np.float32)
    # Weighted RGB distance: 2*dr^2 + 4*dg^2 + 3*db^2
    dr = r[:, :, None] - pal_arr[None, None, :, 0]
    dg = g[:, :, None] - pal_arr[None, None, :, 1]
    db = b[:, :, None] - pal_arr[None, None, :, 2]
    dist = 2.0 * dr * dr + 4.0 * dg * dg + 3.0 * db * db

    if not light:
        skip_obsidian = (r0 >= bg[0] - 1.0) & (g0 >= bg[1] - 1.0) & (b0 >= bg[2] - 1.0)
        dist[:, :, 1] = np.where(skip_obsidian, 1e12, dist[:, :, 1])

    indices = np.argmin(dist, axis=2).astype(np.uint8)
    indices[untouched] = 0
    return indices


def render_scene_frame(
    frame_idx: int,
    light: bool,
    seeds: dict[str, list[dict]],
    layout: dict[str, float],
    sprite_premul: Image.Image,
) -> np.ndarray:
    """Render one frame of the meadow scene and apply the 4x4 Bayer dither."""
    phi = (2.0 * math.pi * frame_idx) / NUM_FRAMES
    palette = LIGHT_PALETTE if light else DARK_PALETTE
    bg_rgb = palette[0]
    ground_y = layout["ground_y"]
    hill_bottom_y = layout["hill_bottom_y"]
    char_size = layout["char_size"]
    char_x = layout["char_x"]
    char_base_y = layout["char_base_y"]
    tree_x = layout["tree_x"]
    canopy_cx = layout["canopy_cx"]
    canopy_cy = layout["canopy_cy"]
    canopy_rx = layout["canopy_rx"]
    canopy_ry = layout["canopy_ry"]

    ss = SUPERSAMPLE
    hi_w, hi_h = BW * ss, BH * ss

    # 1. Exact page background
    canvas = np.empty((BH, BW, 3), dtype=np.float32)
    canvas[:, :] = bg_rgb

    # 2. Sky Layer
    if light:
        # Soft warm lower sky horizon gradient (keeps upper sky & chibi face clear)
        yy = (np.arange(BH, dtype=np.float32) + 0.5)[:, None]
        y_start = ground_y * 0.44
        t_sky = np.clip((yy - y_start) / max(1.0, ground_y - y_start), 0.0, 1.0)
        mask_sky = (yy >= y_start) & (yy <= ground_y)
        r_sky = np.where(t_sky <= 0.5, 233.0, np.interp(t_sky, [0.5, 1.0], [233.0, 154.0]))
        g_sky = np.where(t_sky <= 0.5, 206.0, np.interp(t_sky, [0.5, 1.0], [206.0, 168.0]))
        b_sky = np.where(t_sky <= 0.5, 178.0, np.interp(t_sky, [0.5, 1.0], [178.0, 128.0]))
        a_sky = np.where(
            t_sky <= 0.5,
            np.interp(t_sky, [0.0, 0.5], [0.0, 0.14]),
            np.interp(t_sky, [0.5, 1.0], [0.14, 0.13]),
        )
        a_sky = np.where(mask_sky, a_sky, 0.0)
        sky_rgb = np.stack([r_sky, g_sky, b_sky], axis=-1)
        canvas = sky_rgb * a_sky[:, :, None] + canvas * (1.0 - a_sky[:, :, None])

        # Subtle diagonal sunbeam shaft filtering leftward from canopy
        beam_hi = Image.new("RGBA", (hi_w, hi_h), (0, 0, 0, 0))
        beam_draw = ImageDraw.Draw(beam_hi)
        beam_poly = [
            ((tree_x - char_size * 0.15) * ss, canopy_cy * ss),
            ((tree_x + char_size * 0.08) * ss, (canopy_cy + 6.0) * ss),
            ((char_x - char_size * 0.65) * ss, (ground_y + 4.0) * ss),
            ((char_x - char_size * 1.1) * ss, (ground_y + 4.0) * ss),
        ]
        beam_draw.polygon(beam_poly, fill=(245, 244, 241, 255))
        beam_mask = np.array(beam_hi, dtype=np.float32)[:, :, 3].reshape(BH, ss, BW, ss).mean(axis=(1, 3)) / 255.0

        xx_grid, yy_grid = np.mgrid[0:BH, 0:BW].astype(np.float32)
        xx_grid += 0.5
        yy_grid += 0.5
        p0x, p0y = tree_x, canopy_cy
        p1x, p1y = char_x - char_size * 0.9, ground_y
        vx, vy = p1x - p0x, p1y - p0y
        vlen2 = max(1e-5, vx * vx + vy * vy)
        t_beam = np.clip(((xx_grid - p0x) * vx + (yy_grid - p0y) * vy) / vlen2, 0.0, 1.0)
        a_beam = (1.0 - t_beam) * 0.34 * beam_mask
        beam_paper = np.array([245.0, 244.0, 241.0], dtype=np.float32)
        canvas = beam_paper[None, None, :] * a_beam[:, :, None] + canvas * (1.0 - a_beam[:, :, None])
    else:
        # Twinkling stars (above hill horizon)
        for st in seeds["stars"]:
            sx = int(round(st["u"] * BW))
            sy = int(round(min(ground_y - 12.0, st["v"] * BH)))
            if sy < 5 or sx < 0 or sx >= BW:
                continue
            twinkle = 0.45 + 0.55 * math.sin(2.0 * phi + st["phase"])
            if twinkle > 0.35:
                col = (242, 235, 224) if twinkle > 0.78 else (108, 124, 90)
                canvas[sy, sx] = col
                if st["big"] and twinkle > 0.82:
                    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nx, ny = sx + ox, sy + oy
                        if 0 <= nx < BW and 0 <= ny < BH:
                            canvas[ny, nx] = col

        # Crisp crescent moon in upper-left open sky
        moon_x = round(BW * 0.175)
        moon_y = 26
        moon_r = 7.5
        blend_radial_gradient(
            canvas,
            moon_x,
            moon_y,
            moon_r * 0.8,
            moon_r * 3.8,
            [
                (0.0, (108, 124, 90), 0.24),
                (0.38, (52, 60, 46), 0.16),
                (0.72, (52, 60, 46), 0.05),
                (1.0, (26, 25, 23), 0.0),
            ],
        )

        moon_hi = Image.new("RGBA", (hi_w, hi_h), (0, 0, 0, 0))
        mdraw = ImageDraw.Draw(moon_hi)
        mdraw.ellipse(
            [
                (moon_x - moon_r) * ss,
                (moon_y - moon_r) * ss,
                (moon_x + moon_r) * ss,
                (moon_y + moon_r) * ss,
            ],
            fill=(242, 235, 224, 255),
        )
        cut_x = moon_x + moon_r * 0.42
        cut_y = moon_y - moon_r * 0.18
        cut_r = moon_r * 0.86
        mdraw.ellipse(
            [
                (cut_x - cut_r) * ss,
                (cut_y - cut_r) * ss,
                (cut_x + cut_r) * ss,
                (cut_y + cut_r) * ss,
            ],
            fill=(26, 25, 23, 255),
        )
        composite_rgba_layer(canvas, moon_hi)

        # Soft moonlit sage mist behind tree & character (clipped above hillBottomY)
        blend_radial_gradient(
            canvas,
            char_x + char_size * 0.04,
            ground_y - char_size * 0.44,
            char_size * 0.12,
            char_size * 1.15,
            [
                (0.0, (108, 124, 90), 0.36),
                (0.32, (52, 60, 46), 0.34),
                (0.65, (52, 60, 46), 0.14),
                (0.86, (52, 60, 46), 0.03),
                (1.0, (26, 25, 23), 0.0),
            ],
            y_clip=hill_bottom_y,
        )

    # 3. Distant Rolling Hill
    dist_hi = Image.new("RGBA", (hi_w, hi_h), (0, 0, 0, 0))
    ddraw = ImageDraw.Draw(dist_hi)
    dist_poly = [(0, hill_bottom_y * ss)]
    for x in range(0, BW + 1, 4):
        u = x / BW
        hill_y = (
            ground_y
            - 8.0
            - math.sin(u * math.pi * 1.15 + 0.4) * (BH * 0.042)
            - math.cos(u * math.pi * 2.2) * (BH * 0.014)
        )
        dist_poly.append((x * ss, hill_y * ss))
    dist_poly.append((BW * ss, hill_bottom_y * ss))
    dist_col = (188, 198, 166, 255) if light else (39, 46, 35, 255)
    ddraw.polygon(dist_poly, fill=dist_col)
    composite_rgba_layer(canvas, dist_hi)

    # 4. Foreground Meadow Knoll with vertical gradient + dappled canopy shade + char contact shadow
    knoll_mask_hi = Image.new("RGBA", (hi_w, hi_h), (0, 0, 0, 0))
    kdraw = ImageDraw.Draw(knoll_mask_hi)
    knoll_poly = [(0, hill_bottom_y * ss)]
    for x in range(0, BW + 1, 2):
        knoll_poly.append((x * ss, float(knoll_profile(x, layout)) * ss))
    knoll_poly.append((BW * ss, hill_bottom_y * ss))
    kdraw.polygon(knoll_poly, fill=(255, 255, 255, 255))
    knoll_alpha = (
        np.array(knoll_mask_hi, dtype=np.float32)[:, :, 3]
        .reshape(BH, ss, BW, ss)
        .mean(axis=(1, 3))
        / 255.0
    )

    yy = (np.arange(BH, dtype=np.float32) + 0.5)[:, None]
    y_top = ground_y - 10.0
    t_hill = np.clip((yy - y_top) / max(1.0, hill_bottom_y - y_top), 0.0, 1.0)
    if light:
        h_stops = [
            (0.0, (182, 194, 157)),
            (0.45, (154, 168, 128)),
            (1.0, (154, 168, 128)),
        ]
    else:
        h_stops = [
            (0.0, (75, 89, 65)),
            (0.45, (52, 60, 46)),
            (1.0, (36, 42, 32)),
        ]
    pos_h = [s[0] for s in h_stops]
    hr = np.interp(t_hill, pos_h, [s[1][0] for s in h_stops])
    hg = np.interp(t_hill, pos_h, [s[1][1] for s in h_stops])
    hb = np.interp(t_hill, pos_h, [s[1][2] for s in h_stops])
    hill_rgb = np.broadcast_to(np.stack([hr, hg, hb], axis=-1), (BH, BW, 3))
    canvas = hill_rgb * knoll_alpha[:, :, None] + canvas * (1.0 - knoll_alpha[:, :, None])

    # Dappled shade & contact shadow
    shade_hi = Image.new("RGBA", (hi_w, hi_h), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shade_hi)
    scx = (char_x + char_size * 0.12) * ss
    scy = (ground_y + 3.0) * ss
    srx = (char_size * 0.85) * ss
    sry = max(4.0, char_size * 0.075) * ss
    shade_col = (92, 105, 67, int(round(0.36 * 255))) if light else (14, 14, 13, int(round(0.55 * 255)))
    sdraw.ellipse([scx - srx, scy - sry, scx + srx, scy + sry], fill=shade_col)
    composite_rgba_layer(canvas, shade_hi)

    contact_hi = Image.new("RGBA", (hi_w, hi_h), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(contact_hi)
    ccx = char_x * ss
    ccy = (char_base_y - 1.0) * ss
    crx = (char_size * 0.25) * ss
    cry = max(2.5, char_size * 0.036) * ss
    contact_col = (38, 37, 35, int(round(0.30 * 255))) if light else (14, 14, 13, int(round(0.72 * 255)))
    cdraw.ellipse([ccx - crx, ccy - cry, ccx + crx, ccy + cry], fill=contact_col)
    composite_rgba_layer(canvas, contact_hi)

    # 5. Tree Trunk, Roots & Boughs
    trunk_base_y = ground_y + 4.0
    trunk_top_y = canopy_cy + canopy_ry * 0.15
    trunk_w = max(10.0, char_size * 0.22)

    tree_hi = Image.new("RGBA", (hi_w, hi_h), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(tree_hi)
    bark_col = (78, 71, 60, 255) if light else (28, 27, 24, 255)

    left_edge = quad_bezier_pts(
        (tree_x - trunk_w * 0.95, trunk_base_y + 2.0),
        (tree_x - trunk_w * 0.52, trunk_base_y - char_size * 0.25),
        (tree_x - trunk_w * 0.42, trunk_top_y),
    )
    right_edge = quad_bezier_pts(
        (tree_x + trunk_w * 0.38, trunk_top_y),
        (tree_x + trunk_w * 0.48, trunk_base_y - char_size * 0.25),
        (tree_x + trunk_w * 1.05, trunk_base_y + 3.0),
    )
    trunk_poly = [(x * ss, y * ss) for x, y in (left_edge + right_edge)]
    tdraw.polygon(trunk_poly, fill=bark_col)

    bough_l = quad_bezier_pts(
        (tree_x - trunk_w * 0.15, trunk_top_y + char_size * 0.16),
        (tree_x - char_size * 0.34, canopy_cy + canopy_ry * 0.35),
        (canopy_cx - canopy_rx * 0.48, canopy_cy + canopy_ry * 0.1),
    )
    draw_thick_curve(tdraw, [(x * ss, y * ss) for x, y in bough_l], max(4.0, trunk_w * 0.46) * ss, bark_col)

    bough_r = quad_bezier_pts(
        (tree_x + trunk_w * 0.08, trunk_top_y + char_size * 0.12),
        (tree_x + char_size * 0.25, canopy_cy + canopy_ry * 0.28),
        (canopy_cx + canopy_rx * 0.52, canopy_cy + canopy_ry * 0.12),
    )
    draw_thick_curve(tdraw, [(x * ss, y * ss) for x, y in bough_r], max(3.0, trunk_w * 0.32) * ss, bark_col)

    # Bark edge rim
    rim_col = (154, 168, 128, 255) if light else (108, 124, 90, 255)
    rim_pts = quad_bezier_pts(
        (tree_x - trunk_w * 0.88, trunk_base_y + 1.0),
        (tree_x - trunk_w * 0.48, trunk_base_y - char_size * 0.25),
        (tree_x - trunk_w * 0.38, trunk_top_y),
    )
    draw_thick_curve(tdraw, [(x * ss, y * ss) for x, y in rim_pts], 1.4 * ss, rim_col)

    # Bark grain grooves
    grain_col = (38, 37, 35, 255) if light else (14, 14, 13, 255)
    for g_off in (-1, 0, 1):
        gx = tree_x + g_off * trunk_w * 0.22
        g_pts = quad_bezier_pts(
            (gx, trunk_base_y - char_size * 0.08),
            (gx + 1.5, trunk_base_y - char_size * 0.42),
            (gx - 1.0, trunk_top_y + char_size * 0.14),
        )
        draw_thick_curve(tdraw, [(x * ss, y * ss) for x, y in g_pts], 1.0 * ss, grain_col)

    composite_rgba_layer(canvas, tree_hi)

    def draw_grass(fg_only: bool) -> None:
        gh_hi = Image.new("RGBA", (hi_w, hi_h), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(gh_hi)
        for blade in seeds["grass"]:
            if blade["fg"] != fg_only:
                continue
            gx = blade["u"] * BW
            if fg_only and abs(gx - char_x) > char_size * 0.46:
                continue
            gy = float(knoll_profile(gx, layout)) + (1.5 if fg_only else 0.0)
            wave = math.sin(gx * 0.065 - 2.0 * phi) * 1.6 + math.sin(gx * 0.14 - 3.0 * phi) * 0.55
            sway = wave + blade["lean"]
            tip_x = gx + sway * (blade["h"] / 7.0)
            tip_y = gy - blade["h"]

            if light:
                b_col = (92, 105, 67, 255) if blade["h"] > 8.5 else (154, 168, 128, 255)
            else:
                b_col = (108, 124, 90, 255) if blade["h"] > 8.5 else (52, 60, 46, 255)

            b_pts = quad_bezier_pts(
                (gx, gy + 1.0),
                (gx + sway * 0.35, gy - blade["h"] * 0.5),
                (tip_x, tip_y),
                steps=8,
            )
            draw_thick_curve(gdraw, [(x * ss, y * ss) for x, y in b_pts], blade["thick"] * ss, b_col)

            if not fg_only and blade["flower"]:
                f_col = (245, 244, 241, 255) if light else (218, 186, 152, 255)
                fx = round(tip_x) - 1
                fy = round(tip_y) - 1
                gdraw.rectangle([fx * ss, fy * ss, (fx + 2) * ss, (fy + 2) * ss], fill=f_col)

        composite_rgba_layer(canvas, gh_hi)

    # 6. Back Grass Blades & Wildflowers
    draw_grass(fg_only=False)

    # 7. Seated Sleeping Chibi Character (gentle breathing & sway)
    breathe = math.sin(phi)
    breath_scale_y = 1.0 + 0.015 * breathe
    breath_scale_x = 1.0 - 0.005 * breathe
    sway_angle = 0.012 * breathe

    char_hi = Image.new("RGBA", (hi_w, hi_h), (0, 0, 0, 0))
    draw_sprite_onto_hi(
        char_hi,
        sprite_premul,
        cx_hi=char_x * ss,
        base_y_hi=char_base_y * ss,
        size_hi=char_size * ss,
        scale_x=breath_scale_x,
        scale_y=breath_scale_y,
        angle_rad=sway_angle,
    )
    composite_rgba_layer(canvas, char_hi)

    # 8. Foreground Grass Overlapping Seated Legs
    draw_grass(fg_only=True)

    # 9. Tree Canopy Foliage Clusters (gentle sway)
    canopy_sway_x = math.sin(phi) * 1.8
    canopy_sway_y = math.cos(2.0 * phi) * 0.7

    puffs = [
        (-0.64, 0.18, 0.28, 0.26, 0),
        (-0.22, 0.20, 0.32, 0.28, 0),
        (0.22, 0.22, 0.30, 0.26, 0),
        (0.60, 0.14, 0.26, 0.24, 0),
        (-0.82, 0.02, 0.26, 0.24, 1),
        (-0.46, -0.08, 0.31, 0.30, 1),
        (-0.05, -0.10, 0.34, 0.32, 1),
        (0.38, -0.06, 0.31, 0.28, 1),
        (0.72, 0.00, 0.24, 0.22, 1),
        (-0.54, -0.24, 0.24, 0.22, 2),
        (-0.18, -0.34, 0.28, 0.25, 2),
        (0.20, -0.30, 0.26, 0.24, 2),
        (0.50, -0.20, 0.22, 0.20, 2),
    ]
    can_hi = Image.new("RGBA", (hi_w, hi_h), (0, 0, 0, 0))
    candraw = ImageDraw.Draw(can_hi)
    tier_colors_light = [(72, 84, 52, 255), (92, 105, 67, 255), (154, 168, 128, 255)]
    tier_colors_dark = [(34, 41, 30, 255), (52, 60, 46, 255), (108, 124, 90, 255)]

    for i, (ox, oy, rx_f, ry_f, tier) in enumerate(puffs):
        px = canopy_cx + ox * canopy_rx + canopy_sway_x * (0.7 + (i % 3) * 0.18)
        py = canopy_cy + oy * canopy_ry + canopy_sway_y
        prx = rx_f * canopy_rx
        pry = ry_f * canopy_ry
        col = tier_colors_light[tier] if light else tier_colors_dark[tier]
        candraw.ellipse(
            [(px - prx) * ss, (py - pry) * ss, (px + prx) * ss, (py + pry) * ss],
            fill=col,
        )
    composite_rgba_layer(canvas, can_hi)

    # 10. Soft Dithered Bottom Horizon Dissolve
    dissolve_top = max(ground_y + 1.0, hill_bottom_y - 12.0)
    yy = (np.arange(BH, dtype=np.float32) + 0.5)[:, None]
    t_dis = np.clip((yy - dissolve_top) / max(1.0, hill_bottom_y - dissolve_top), 0.0, 1.0)
    t_dis = np.where(yy >= dissolve_top, t_dis, 0.0)
    bg_arr = np.array(bg_rgb, dtype=np.float32)
    canvas = bg_arr[None, None, :] * t_dis[:, :, None] + canvas * (1.0 - t_dis[:, :, None])

    # 11. Pulsing & bobbing meadow fireflies in dark mode (dithered smoothly into Layer 1)
    if not light:
        for idx_ff, ff in enumerate(seeds["fireflies"]):
            fx = ff["u"] * BW + math.sin(phi + ff["phase"]) * ff["amp_x"]
            fy = ground_y - 4.0 - ff["v"] * (char_size * 0.55) + math.cos(phi + ff["phase"]) * ff["amp_y"]
            pulse = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(phi * (1 if idx_ff % 2 == 0 else 2) + ff["phase"])) ** 2
            if pulse > 0.3:
                blend_radial_gradient(
                    canvas,
                    fx,
                    fy,
                    0.5,
                    4.5,
                    [
                        (0.0, (242, 235, 224), pulse),
                        (0.5, (218, 186, 152), pulse * 0.45),
                        (1.0, (26, 25, 23), 0.0),
                    ],
                )

    return bayer_dither(canvas, palette, light)


def encode_mask_to_rect_path(mask: np.ndarray) -> str:
    """RLE + vertical rectangle merging for compact, crisp pixel paths."""
    h, w = mask.shape
    active_rects: dict[tuple[int, int], int] = {}
    finished: list[tuple[int, int, int, int]] = []

    for y in range(h):
        row = mask[y]
        runs: list[tuple[int, int]] = []
        if np.any(row):
            # Fast run detection
            padded = np.zeros(w + 2, dtype=np.int8)
            padded[1:-1] = row
            diffs = padded[1:] - padded[:-1]
            starts = np.where(diffs == 1)[0]
            ends = np.where(diffs == -1)[0]
            for s, e in zip(starts, ends):
                runs.append((int(s), int(e - s)))

        run_set = set(runs)
        next_active: dict[tuple[int, int], int] = {}
        for key, start_y in active_rects.items():
            if key in run_set:
                next_active[key] = start_y
            else:
                finished.append((key[0], start_y, key[1], y - start_y))
        for key in runs:
            if key not in next_active:
                next_active[key] = y
        active_rects = next_active

    for key, start_y in active_rects.items():
        finished.append((key[0], start_y, key[1], h - start_y))

    finished.sort(key=lambda r: (r[1], r[0]))
    parts = [f"M{x} {y}h{rw}v{rh}h-{rw}z" for x, y, rw, rh in finished]
    return "".join(parts)


def build_dithered_cloud_group(
    palette: list[tuple[int, int, int]], cx: int, cy: int, w: int, h: int, cls: str
) -> str:
    """Create a tiny Bayer-dithered sunlit cloud puff SVG group for light-mode Layer 2."""
    # Render soft ellipse puff on a small canvas against bg, then Bayer dither and keep non-bg pixels
    pad = 4
    gw = w + pad * 2
    gh = h + pad * 2
    hi_w, hi_h = gw * SUPERSAMPLE, gh * SUPERSAMPLE
    hi = Image.new("RGBA", (hi_w, hi_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(hi)
    col = (233, 206, 178, int(round(0.55 * 255)))
    ccx, ccy = gw * 0.5, gh * 0.5
    ellipses = [
        (ccx, ccy, w * 0.52, w * 0.19),
        (ccx - w * 0.24, ccy + 1.2, w * 0.30, w * 0.14),
        (ccx + w * 0.26, ccy + 1.2, w * 0.28, w * 0.13),
    ]
    for ex, ey, erx, ery in ellipses:
        draw.ellipse(
            [
                (ex - erx) * SUPERSAMPLE,
                (ey - ery) * SUPERSAMPLE,
                (ex + erx) * SUPERSAMPLE,
                (ey + ery) * SUPERSAMPLE,
            ],
            fill=col,
        )

    bg_rgb = palette[0]
    arr = np.array(hi, dtype=np.float32) / 255.0
    a = arr[:, :, 3:4]
    premul = np.concatenate([arr[:, :, :3] * a, a], axis=2)
    down = premul.reshape(gh, SUPERSAMPLE, gw, SUPERSAMPLE, 4).mean(axis=(1, 3))
    canvas = np.empty((gh, gw, 3), dtype=np.float32)
    canvas[:, :] = bg_rgb
    canvas = down[:, :, :3] * 255.0 + canvas * (1.0 - down[:, :, 3:4])

    bayer_tiled = np.tile(BAYER_4X4, (gh // 4 + 1, gw // 4 + 1))[:gh, :gw]
    d = bayer_tiled * BAYER_SPREAD
    pal_arr = np.array(palette, dtype=np.float32)
    r = canvas[:, :, 0] + d
    g = canvas[:, :, 1] + d
    b = canvas[:, :, 2] + d
    dr = r[:, :, None] - pal_arr[None, None, :, 0]
    dg = g[:, :, None] - pal_arr[None, None, :, 1]
    db = b[:, :, None] - pal_arr[None, None, :, 2]
    dist = 2.0 * dr * dr + 4.0 * dg * dg + 3.0 * db * db
    idx = np.argmin(dist, axis=2)

    ox = cx - gw // 2
    oy = cy - gh // 2
    paths = []
    for p_idx in range(1, len(palette)):
        mask = (idx == p_idx).astype(np.uint8)
        if np.any(mask):
            d_str = encode_mask_to_rect_path(mask)
            if d_str:
                paths.append(
                    f'<path fill="{rgb_hex(palette[p_idx])}" transform="translate({ox},{oy})" d="{d_str}"/>'
                )
    return f'<g class="{cls}">' + "".join(paths) + "</g>"


def build_layer2_overlays(light: bool, layout: dict[str, float]) -> tuple[str, str, str]:
    """Return (css_rules, bg_svg_elements, fg_svg_elements) for smooth asynchronous Layer 2 overlays."""
    char_x = layout["char_x"]
    char_base_y = layout["char_base_y"]
    char_size = layout["char_size"]
    canopy_cx = layout["canopy_cx"]
    canopy_cy = layout["canopy_cy"]
    canopy_rx = layout["canopy_rx"]
    canopy_ry = layout["canopy_ry"]

    z_col = "#262523" if light else "#f2ebe0"
    leaf_col = "#5c6943" if light else "#6c7c5a"

    zx0 = round(char_x + char_size * 0.08)
    zy0 = round(char_base_y - char_size * 0.74)

    css_parts = [
        """      @keyframes fSlot {
        0% { opacity: 1; }
        8.333% { opacity: 0; }
        100% { opacity: 0; }
      }
      @keyframes zRise {
        0%   { transform: translate(0px, 0px); opacity: 0; }
        16%  { transform: translate(2px, -3px); opacity: 0.90; }
        52%  { transform: translate(4px, -8px); opacity: 0.85; }
        82%  { transform: translate(5px, -13px); opacity: 0.40; }
        100% { transform: translate(7px, -16px); opacity: 0; }
      }
      @keyframes leafFallA {
        0%   { transform: translate(0px, 0px); opacity: 0; }
        12%  { opacity: 0.95; }
        38%  { transform: translate(-12px, 16px); opacity: 0.92; }
        68%  { transform: translate(-19px, 36px); opacity: 0.82; }
        90%  { opacity: 0.35; }
        100% { transform: translate(-31px, 56px); opacity: 0; }
      }
      @keyframes leafFallB {
        0%   { transform: translate(0px, 0px); opacity: 0; }
        15%  { opacity: 0.92; }
        45%  { transform: translate(-8px, 21px); opacity: 0.88; }
        75%  { transform: translate(-24px, 40px); opacity: 0.75; }
        100% { transform: translate(-36px, 60px); opacity: 0; }
      }"""
    ]

    for k in range(1, NUM_FRAMES):
        delay = -round(LOOP_DURATION - k * FRAME_DURATION, 2)
        css_parts.append(
            f"      .f{k} {{ animation: fSlot {LOOP_DURATION}s steps(1, end) {delay}s infinite; }}"
        )

    css_parts.append(
        """      .z1 { animation: zRise 3.9s linear 0s infinite; }
      .z2 { animation: zRise 3.9s linear -1.3s infinite; }
      .z3 { animation: zRise 3.9s linear -2.6s infinite; }
      .lf1 { animation: leafFallA 7.4s linear -0.8s infinite; }
      .lf2 { animation: leafFallB 8.9s linear -3.4s infinite; }
      .lf3 { animation: leafFallA 6.8s linear -5.1s infinite; }
      .lf4 { animation: leafFallB 9.4s linear -2.1s infinite; }"""
    )

    # Pixel Z bitmap path from drawPixelZ(): (0,0,4,1), (2,1,1,1), (1,2,1,1), (0,3,4,1)
    z_d = "M0 0h4v1h-4zM2 1h1v1h-1zM1 2h1v1h-1zM0 3h4v1h-4z"
    bg_parts: list[str] = []
    fg_parts: list[str] = []
    for i, cls in enumerate(("z1", "z2", "z3")):
        ox = zx0 + (i - 1)
        fg_parts.append(
            f'      <g class="{cls}"><path fill="{z_col}" transform="translate({ox},{zy0})" d="{z_d}"/></g>'
        )

    leaf_starts = [
        (round(canopy_cx - canopy_rx * 0.35), round(canopy_cy + canopy_ry * 0.45), "lf1"),
        (round(canopy_cx + canopy_rx * 0.18), round(canopy_cy + canopy_ry * 0.35), "lf2"),
        (round(canopy_cx - canopy_rx * 0.12), round(canopy_cy + canopy_ry * 0.55), "lf3"),
        (round(canopy_cx + canopy_rx * 0.42), round(canopy_cy + canopy_ry * 0.30), "lf4"),
    ]
    for lx, ly, cls in leaf_starts:
        fg_parts.append(
            f'      <g class="{cls}"><rect x="{lx}" y="{ly}" width="2" height="1" fill="{leaf_col}"/></g>'
        )

    if not light:
        css_parts.append(
            """      @keyframes moteDriftA {
        0%   { transform: translate(0px, 0px); opacity: 0.15; }
        25%  { transform: translate(7px, -4px); opacity: 0.95; }
        50%  { transform: translate(13px, 1px); opacity: 0.35; }
        75%  { transform: translate(5px, -5px); opacity: 0.90; }
        100% { transform: translate(0px, 0px); opacity: 0.15; }
      }
      @keyframes moteDriftB {
        0%   { transform: translate(0px, 0px); opacity: 0.85; }
        30%  { transform: translate(-8px, -5px); opacity: 0.20; }
        65%  { transform: translate(-14px, 2px); opacity: 0.95; }
        100% { transform: translate(0px, 0px); opacity: 0.85; }
      }
      .ff1 { animation: moteDriftA 7.8s ease-in-out -1.1s infinite; }
      .ff2 { animation: moteDriftB 9.2s ease-in-out -4.3s infinite; }
      .ff3 { animation: moteDriftA 10.6s ease-in-out -6.7s infinite; }
      .ff4 { animation: moteDriftB 8.4s ease-in-out -2.9s infinite; }
      .ff5 { animation: moteDriftA 11.4s ease-in-out -5.5s infinite; }"""
        )
        motes = [
            (28, 72, "ff1"),
            (86, 78, "ff2"),
            (122, 69, "ff3"),
            (226, 76, "ff4"),
            (256, 71, "ff5"),
        ]
        for mx, my, cls in motes:
            fg_parts.append(
                f'      <g class="{cls}">'
                f'<rect x="{mx}" y="{my}" width="1" height="1" fill="#f2ebe0"/>'
                f'<rect x="{mx - 1}" y="{my}" width="1" height="1" fill="#daba98"/>'
                f'<rect x="{mx + 1}" y="{my}" width="1" height="1" fill="#daba98"/>'
                f'<rect x="{mx}" y="{my - 1}" width="1" height="1" fill="#6c7c5a"/>'
                f'<rect x="{mx}" y="{my + 1}" width="1" height="1" fill="#6c7c5a"/>'
                f"</g>"
            )
    else:
        css_parts.append(
            """      @keyframes cloudDriftA {
        0%   { transform: translate(-45px, 0px); }
        100% { transform: translate(295px, 0px); }
      }
      @keyframes pollenDriftA {
        0%   { transform: translate(0px, 0px); opacity: 0; }
        20%  { opacity: 0.85; }
        80%  { opacity: 0.75; }
        100% { transform: translate(-24px, 12px); opacity: 0; }
      }
      @keyframes pollenDriftB {
        0%   { transform: translate(0px, 0px); opacity: 0; }
        25%  { opacity: 0.80; }
        75%  { opacity: 0.75; }
        100% { transform: translate(-18px, -10px); opacity: 0; }
      }
      .cl1 { animation: cloudDriftA 38s linear -8s infinite; }
      .cl2 { animation: cloudDriftA 52s linear -26s infinite; }
      .cl3 { animation: cloudDriftA 44s linear -36s infinite; }
      .pl1 { animation: pollenDriftA 8.1s linear -1.2s infinite; }
      .pl2 { animation: pollenDriftB 9.6s linear -4.8s infinite; }
      .pl3 { animation: pollenDriftA 11.2s linear -7.1s infinite; }
      .pl4 { animation: pollenDriftB 7.6s linear -2.5s infinite; }
      .pl5 { animation: pollenDriftA 10.4s linear -5.9s infinite; }
      .pl6 { animation: pollenDriftB 11.8s linear -9.3s infinite; }"""
        )
        bg_parts.append("      " + build_dithered_cloud_group(LIGHT_PALETTE, 0, 18, 30, 12, "cl1"))
        bg_parts.append("      " + build_dithered_cloud_group(LIGHT_PALETTE, 0, 14, 22, 10, "cl2"))
        bg_parts.append("      " + build_dithered_cloud_group(LIGHT_PALETTE, 0, 23, 25, 11, "cl3"))
        for px, py, cls in (
            (58, 42, "pl1"),
            (108, 56, "pl2"),
            (142, 34, "pl3"),
            (196, 52, "pl4"),
            (236, 44, "pl5"),
            (76, 68, "pl6"),
        ):
            fg_parts.append(
                f'      <g class="{cls}"><rect x="{px}" y="{py}" width="1" height="1" fill="#e9ceb2"/></g>'
            )

    return "\n".join(css_parts), "\n".join(bg_parts), "\n".join(fg_parts)


def read_existing_stats(path: Path) -> tuple[str, str]:
    """Preserve live repository & contribution counts synced by GitHub Actions."""
    repos, contribs = "7", "157"
    if not path.exists():
        return repos, contribs
    text = path.read_text(encoding="utf-8")
    m_repos = re.search(r'<text id="stat-repos"[^>]*>([^<]*)</text>', text)
    m_contribs = re.search(r'<text id="stat-contribs"[^>]*>([^<]*)</text>', text)
    if m_repos and m_repos.group(1).strip():
        repos = m_repos.group(1).strip()
    if m_contribs and m_contribs.group(1).strip():
        contribs = m_contribs.group(1).strip()
    return repos, contribs


def build_svg(
    light: bool,
    seeds: dict[str, list[dict]],
    layout: dict[str, float],
    sprite_premul: Image.Image,
    repos: str,
    contribs: str,
) -> str:
    palette = LIGHT_PALETTE if light else DARK_PALETTE
    pal_hex = [rgb_hex(c) for c in palette]
    bg_hex = pal_hex[0]

    frames = [
        render_scene_frame(k, light, seeds, layout, sprite_premul)
        for k in range(NUM_FRAMES)
    ]

    # Frame 0 base paths (all non-background pixels)
    f0 = frames[0]
    base_paths: list[str] = []
    for p_idx in range(1, len(palette)):
        mask = (f0 == p_idx).astype(np.uint8)
        if np.any(mask):
            d_str = encode_mask_to_rect_path(mask)
            if d_str:
                base_paths.append(f'      <path fill="{pal_hex[p_idx]}" d="{d_str}"/>')

    # Diff frames 1..NUM_FRAMES-1 (include bg color pixels so moving edges erase cleanly)
    diff_groups: list[str] = []
    for k in range(1, NUM_FRAMES):
        fk = frames[k]
        diff = fk != f0
        grp_paths: list[str] = []
        for p_idx in range(len(palette)):
            mask = (diff & (fk == p_idx)).astype(np.uint8)
            if np.any(mask):
                d_str = encode_mask_to_rect_path(mask)
                if d_str:
                    grp_paths.append(f'        <path fill="{pal_hex[p_idx]}" d="{d_str}"/>')
        diff_groups.append(
            f'      <g class="f{k}">\n' + "\n".join(grp_paths) + "\n      </g>"
        )

    css_rules, layer2_bg_svg, layer2_fg_svg = build_layer2_overlays(light, layout)

    # Theme chrome tokens matching existing card design
    if light:
        card_bg = "#ffffff"
        stroke = "#d0d7de"
        text_primary = "#1f2328"
        text_secondary = "#57606a"
        text_label = "#6e7781"
    else:
        card_bg = "#0d1014"
        stroke = "#262a33"
        text_primary = "#f3f4f6"
        text_secondary = "#8b949e"
        text_label = "#6e7681"

    bg_block = (layer2_bg_svg + "\n") if layer2_bg_svg else ""

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W}" height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}" fill="none">\n'
        f"  <defs>\n"
        f'    <clipPath id="banner-clip">\n'
        f'      <rect x="1" y="37" width="{BANNER_W}" height="{BANNER_H}"/>\n'
        f"    </clipPath>\n"
        f"    <style>\n"
        f"{css_rules}\n"
        f"    </style>\n"
        f"  </defs>\n\n"
        f'  <rect x="0.5" y="0.5" width="{SVG_W - 1}" height="{SVG_H - 1}" rx="2" fill="{card_bg}" stroke="{stroke}"/>\n\n'
        f"  <!-- Top bar -->\n"
        f'  <text x="16" y="23" fill="{text_primary}" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="12" font-weight="600">ali tanting</text>\n'
        f'  <g shape-rendering="crispEdges">\n'
        f'    <rect x="105" y="14" width="3" height="3" fill="#eab308"/>\n'
        f'    <rect x="110" y="14" width="3" height="3" fill="#52525b"/>\n'
        f'    <rect x="105" y="19" width="3" height="3" fill="#52525b"/>\n'
        f'    <rect x="110" y="19" width="3" height="3" fill="#facc15"/>\n'
        f"  </g>\n"
        f'  <text x="121" y="23" fill="{text_secondary}" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" letter-spacing="0.08em">BUILDING</text>\n'
        f'  <text x="832" y="23" text-anchor="end" fill="{text_secondary}" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11.5">github.com/a-ldnstntng</text>\n\n'
        f'  <line x1="1" y1="36.5" x2="847" y2="36.5" stroke="{stroke}"/>\n\n'
        f"  <!-- Animated 4x4 Bayer-dithered sleeping chibi meadow scene -->\n"
        f'  <g clip-path="url(#banner-clip)" shape-rendering="crispEdges">\n'
        f'    <rect x="1" y="37" width="{BANNER_W}" height="{BANNER_H}" fill="{bg_hex}"/>\n'
        f'    <g transform="translate(1,37) scale({SCALE})">\n'
        + bg_block
        + "\n".join(base_paths)
        + "\n"
        + "\n".join(diff_groups)
        + "\n"
        + layer2_fg_svg
        + "\n"
        f"    </g>\n"
        f"  </g>\n\n"
        f'  <line x1="1" y1="337.5" x2="847" y2="337.5" stroke="{stroke}"/>\n\n'
        f"  <!-- Identity split -->\n"
        f'  <line x1="504.5" y1="338" x2="504.5" y2="517" stroke="{stroke}"/>\n\n'
        f'  <text x="24" y="396" fill="{text_primary}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Helvetica, Arial, sans-serif" font-size="34" font-weight="700" letter-spacing="-0.03em">ali tanting</text>\n'
        f'  <text x="24" y="422" fill="{text_secondary}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Helvetica, Arial, sans-serif" font-size="13">Building web apps, tools, and small indie games.</text>\n\n'
        f'  <text x="24" y="474" fill="{text_label}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5" letter-spacing="0.06em">HANDLE</text>\n'
        f'  <text x="92" y="474" fill="{text_primary}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="12.5">@a-ldnstntng</text>\n\n'
        f"  <!-- 2x2 metrics grid -->\n"
        f'  <line x1="676.5" y1="338" x2="676.5" y2="517" stroke="{stroke}"/>\n'
        f'  <line x1="505" y1="427.5" x2="847" y2="427.5" stroke="{stroke}"/>\n\n'
        f'  <text x="524" y="366" fill="{text_label}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5" letter-spacing="0.06em">REPOSITORIES</text>\n'
        f'  <text id="stat-repos" x="524" y="399" fill="{text_primary}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif" font-size="16" font-weight="700">{repos}</text>\n\n'
        f'  <text x="696" y="366" fill="{text_label}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5" letter-spacing="0.06em">CONTRIBUTIONS</text>\n'
        f'  <text id="stat-contribs" x="696" y="399" fill="{text_primary}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif" font-size="16" font-weight="700">{contribs}</text>\n\n'
        f'  <text x="524" y="456" fill="{text_label}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5" letter-spacing="0.06em">STATUS</text>\n'
        f'  <text x="524" y="489" fill="{text_primary}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif" font-size="16" font-weight="700">active</text>\n\n'
        f'  <text x="696" y="456" fill="{text_label}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5" letter-spacing="0.06em">FOCUS</text>\n'
        f'  <text x="696" y="489" fill="{text_primary}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif" font-size="16" font-weight="700">web &amp; games</text>\n'
        f"</svg>\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate animated Bayer-dithered meadow hero SVGs.")
    parser.add_argument("--sprite", type=Path, default=DEFAULT_SPRITE, help="Path to character-asleep.png")
    args = parser.parse_args()

    if not args.sprite.exists():
        raise FileNotFoundError(f"Character sprite not found: {args.sprite}")

    seeds = build_seeds()
    layout = compute_layout()
    day_sprite, night_sprite = bake_sprite_variants(args.sprite)

    target_px = int(round(layout["char_size"] * SUPERSAMPLE))
    day_ready = prepare_sprite(day_sprite, target_px)
    night_ready = prepare_sprite(night_sprite, target_px)

    targets = [
        ("hero-dark.svg", False, night_ready),
        ("hero-light.svg", True, day_ready),
    ]

    for filename, is_light, sprite_premul in targets:
        out_path = ASSETS / filename
        repos, contribs = read_existing_stats(out_path)
        svg_text = build_svg(is_light, seeds, layout, sprite_premul, repos, contribs)
        ET.fromstring(svg_text)  # validate well-formed XML
        out_path.write_text(svg_text, encoding="utf-8")
        print(f"Wrote {out_path} ({out_path.stat().st_size:,} bytes) [repos={repos}, contribs={contribs}]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
