import os
import math
import io
import struct
import numpy as np
from PIL import Image, ImageFilter

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def smoothstep(edge0, edge1, x):
    t = np.clip((x - edge0) / (edge1 - edge0 + 1e-12), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def sd_segment(px, py, ax, ay, bx, by):
    pax = px - ax
    pay = py - ay
    bax = bx - ax
    bay = by - ay
    denom = bax * bax + bay * bay + 1e-12
    h = np.clip((pax * bax + pay * bay) / denom, 0.0, 1.0)
    dx = pax - bax * h
    dy = pay - bay * h
    return np.sqrt(dx * dx + dy * dy)


def sd_polygon(px, py, verts):
    n = len(verts)
    d2 = np.full_like(px, 1e9, dtype=np.float32)
    s = np.ones_like(px, dtype=np.float32)

    for i in range(n):
        j = (i - 1) % n
        vx, vy = verts[i]
        wx, wy = verts[j]
        ex, ey = wx - vx, wy - vy
        px_v = px - vx
        py_v = vy
        py_v = py - vy
        denom = ex * ex + ey * ey + 1e-12
        t = np.clip((px_v * ex + py_v * ey) / denom, 0.0, 1.0)
        bx = px_v - ex * t
        by = py_v - ey * t
        d2 = np.minimum(d2, bx * bx + by * by)

        c1 = py >= vy
        c2 = py < wy
        c3 = ex * py_v > ey * px_v
        cond = (c1 & c2 & c3) | ((~c1) & (~c2) & (~c3))
        s = np.where(cond, -s, s)

    return s * np.sqrt(d2)


def alpha_over(dst, src_rgb, src_a):
    src_a = np.clip(src_a, 0.0, 1.0)[..., None]
    out_a = src_a + dst[..., 3:4] * (1.0 - src_a)
    out_rgb = src_rgb * src_a + dst[..., :3] * (1.0 - src_a)
    return np.concatenate([out_rgb, out_a], axis=-1)


def additive_glow(dst, glow_rgb, glow_a):
    glow_a = np.clip(glow_a, 0.0, 1.0)[..., None]
    out_rgb = np.clip(dst[..., :3] + glow_rgb * glow_a, 0.0, 1.0)
    out_a = np.clip(dst[..., 3:4] + glow_a * 0.94, 0.0, 1.0)
    return np.concatenate([out_rgb, out_a], axis=-1)


def smooth_arc_distance(px, py, ax, ay, bx, by, curve_amp, freq, phase_shift, n_pts=24):
    """
    Smooth, tapered, high-tech electric plasma arc between (ax, ay) and (bx, by).
    Returns (distance_field, taper_weight) so ends taper cleanly to needle points.
    """
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy) + 1e-8
    nx, ny = -dy / length, dx / length

    pts = []
    for k in range(n_pts + 1):
        t = k / n_pts
        env = math.sin(t * math.pi)  # 0 at ends, 1 in middle
        wave = math.sin(t * freq * math.pi - phase_shift) * 0.35 + 0.65
        offset = curve_amp * env * wave
        pts.append((ax + dx * t + nx * offset, ay + dy * t + ny * offset, env))

    d_min = np.full_like(px, 1e9, dtype=np.float32)
    taper_out = np.zeros_like(px, dtype=np.float32)
    for i in range(n_pts):
        x0, y0, e0 = pts[i]
        x1, y1, e1 = pts[i + 1]
        seg_d = sd_segment(px, py, x0, y0, x1, y1)
        mask = seg_d < d_min
        d_min = np.where(mask, seg_d, d_min)
        taper_out = np.where(mask, 0.5 * (e0 + e1), taper_out)
    return d_min, taper_out


def midpoint_lightning(ax, ay, bx, by, rng, depth=3, disp=0.065):
    """Recursive midpoint-displacement lightning segments + forked offshoots."""
    pts = [(ax, ay), (bx, by)]
    cur_disp = disp
    for _ in range(depth):
        new_pts = [pts[0]]
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
            dx, dy = x1 - x0, y1 - y0
            length = math.hypot(dx, dy) + 1e-8
            nx, ny = -dy / length, dx / length
            offset = rng.uniform(-cur_disp, cur_disp)
            new_pts.append((mx + nx * offset, my + ny * offset))
            new_pts.append((x1, y1))
        pts = new_pts
        cur_disp *= 0.52

    segs = [(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], 1.0) for i in range(len(pts) - 1)]

    # Add 3 crisp forked offshoot branches from nodes
    for idx in (len(pts) // 4, len(pts) // 2, (3 * len(pts)) // 4):
        if 0 < idx < len(pts) - 1:
            sx, sy = pts[idx]
            ang = rng.uniform(-1.35, 1.35)
            dx = (bx - ax) * rng.uniform(0.22, 0.36)
            dy = (by - ay) * rng.uniform(0.22, 0.36)
            ca, sa = math.cos(ang), math.sin(ang)
            ex = sx + (dx * ca - dy * sa)
            ey = sy + (dx * sa + dy * ca)
            mx = 0.5 * (sx + ex) + rng.uniform(-0.022, 0.022)
            my = 0.5 * (sy + ey) + rng.uniform(-0.022, 0.022)
            segs.append((sx, sy, mx, my, 0.82))
            segs.append((mx, my, ex, ey, 0.55))

    return segs


def eval_lightning_segs(px, py, segs):
    """Return (min_distance, intensity_weight) to a list of lightning segments."""
    d_min = np.full_like(px, 1e9, dtype=np.float32)
    w_out = np.zeros_like(px, dtype=np.float32)
    for x0, y0, x1, y1, w in segs:
        d = sd_segment(px, py, x0, y0, x1, y1)
        mask = d < d_min
        d_min = np.where(mask, d, d_min)
        w_out = np.where(mask, w, w_out)
    return d_min, w_out


def crystalline_fractal_zoom(px, py, cx, cy, phase, theta):
    """
    Infinite-zoom recursive crystalline wireframe fractal (inspired by fractal
    sanctuary, but using an 8-fold diamond/octagon lattice in dark obsidian +
    razor-thin glowing violet/cyan edges).
    """
    dx = px - cx
    dy = py - cy
    wire_accum = np.zeros_like(px, dtype=np.float32)
    facet_accum = np.zeros_like(px, dtype=np.float32)

    for k in range(2):
        u = (phase + k / 2.0) % 1.0
        w = math.sin(u * math.pi) ** 1.3
        scale = 1.5 * (2.6 ** (1.0 - u))  # Spacious, open infinite inward zoom

        ang = theta * 0.25 + k * 0.6
        ca, sa = math.cos(ang), math.sin(ang)
        zx = (dx * ca - dy * sa) * scale
        zy = (dx * sa + dy * ca) * scale

        # 2-level crystalline subdivision (clean, spacious, NOT cluttered)
        min_edge = np.full_like(px, 1e9, dtype=np.float32)
        for it in range(2):
            zx = np.abs(np.mod(zx + 1.0, 2.0) - 1.0)
            zy = np.abs(np.mod(zy + 1.0, 2.0) - 1.0)
            d_box = np.minimum(1.0 - zx, 1.0 - zy)
            d_diag = np.abs(zx - zy) * 0.707
            d_line = np.minimum(d_box, d_diag)
            min_edge = np.minimum(min_edge, d_line * (1.0 + it * 0.2))
            zx, zy = (zx - zy) * 1.414, (zx + zy) * 1.414

        # Vector-crisp glowing crystalline wireframe lines (tight smoothstep edge)
        wire = 1.0 - smoothstep(0.012, 0.036, min_edge)
        wire_accum += wire * w
        facet_accum += (1.0 - smoothstep(0.04, 0.14, min_edge)) * w

    wire_accum = np.clip(wire_accum * 0.78, 0.0, 1.0)
    facet_accum = np.clip(facet_accum * 0.28, 0.0, 1.0)
    return wire_accum, facet_accum


def render_violent_prism_frame(size: int, frame_idx: int, n_frames: int, mode: str = "arrow") -> Image.Image:
    """
    Razor-thin Infinite Crystalline Fractal Zoom (dark obsidian depth + glowing
    violet/cyan facets) + Real Forked Exterior Lightning + Graceful Cyber-Prism Shine.
    """
    coords = (np.arange(size, dtype=np.float32) + 0.5) / size
    x, y = np.meshgrid(coords, coords)
    canvas = np.zeros((size, size, 4), dtype=np.float32)

    phase = frame_idx / n_frames
    f_phase = (phase * 3.0) % 1.0  # Keep fractal zoom at normal speed while shine is 3x slower (~3.6s)!
    tau = 2.0 * math.pi
    theta = f_phase * tau
    obsidian = np.array([0.00, 0.00, 0.00], dtype=np.float32)  # Pure jet-black 1px contrast border

    # Ice-Blue / Electric-Cyan + Pure White-Hot Core (stands out on blue wallpapers via bright ice-white/cyan rim + jet-black outer border!)
    c_cyan = np.array([0.00, 0.92, 1.00], dtype=np.float32)    # Electric Cyan
    c_indigo = np.array([0.08, 0.36, 1.00], dtype=np.float32)  # Deep Cobalt Blue facet
    c_violet = np.array([0.38, 0.88, 1.00], dtype=np.float32)  # Bright Ice-Blue fractal & arcs
    c_core = np.array([0.98, 1.00, 1.00], dtype=np.float32)    # Pure White-Hot core

    # Every single frame gets fresh erratic lightning!
    bolt_step = frame_idx

    # -----------------------------------------------------------------------
    # I-BEAM: Sleek Obsidian + Cyan-Bevel Bar (zero exterior lightning) + Slow Shine
    # -----------------------------------------------------------------------
    if mode == "ibeam":
        cx = 0.50
        d_top = sd_segment(x, y, 0.37, 0.14, 0.63, 0.14)
        d_bot = sd_segment(x, y, 0.37, 0.86, 0.63, 0.86)
        d_rail = sd_segment(x, y, cx, 0.14, cx, 0.86)
        d_struct = np.minimum(d_rail, np.minimum(d_top, d_bot))

        canvas = alpha_over(canvas, obsidian, (1.0 - smoothstep(0.016, 0.028, d_struct - 0.014)) * 0.99)

        bar_fill = 1.0 - smoothstep(0.010, 0.016, d_struct)
        wire, _ = crystalline_fractal_zoom(x, y, cx, 0.50, f_phase, theta)
        bar_rgb = np.array([0.01, 0.03, 0.08], dtype=np.float32) + c_violet * (0.75 * wire[..., None])
        canvas = alpha_over(canvas, bar_rgb, bar_fill * 0.99)

        bevel = 1.0 - smoothstep(0.005, 0.010, np.abs(d_struct - 0.014))
        canvas = additive_glow(canvas, c_cyan * 0.45 + c_core * 0.55, bevel * 0.98)

        # Very slow Cyber-Prism shine (~3.6s cycle)
        shine_y = phase * 1.85 - 0.45
        shine = np.exp(-(((y - shine_y) / 0.075) ** 2))
        canvas = additive_glow(canvas, c_core, shine * (d_struct < 0.022) * 0.85)

        rgba = (np.clip(canvas, 0.0, 1.0) * 255.0).astype(np.uint8)
        return Image.fromarray(rgba, mode="RGBA")

    # -----------------------------------------------------------------------
    # BUSY / CROSSHAIR: Crystalline Fractal Core + Clean Razor Ring + Slow Shine
    # -----------------------------------------------------------------------
    if mode == "busy":
        cx, cy = 0.50, 0.50
        dx, dy = x - cx, y - cy
        r = np.sqrt(dx * dx + dy * dy) + 1e-8
        ang = np.arctan2(dy, dx)

        saw_ang = ang - theta * 2.0
        saw_wave = (saw_ang * 6.0 / tau) % 1.0
        saw_r = 0.23 + 0.11 * saw_wave
        d_saw = np.abs(r - saw_r)

        canvas = alpha_over(canvas, obsidian, (1.0 - smoothstep(0.018, 0.036, np.minimum(d_saw, r - 0.21))) * 0.98)

        wire, facet = crystalline_fractal_zoom(x, y, cx, cy, f_phase, theta)
        disc_mask = 1.0 - smoothstep(0.19, 0.23, r)
        disc_rgb = (
            np.array([0.01, 0.03, 0.08], dtype=np.float32)
            + c_indigo * (0.35 * facet[..., None])
            + c_violet * (0.75 * wire[..., None])
            + c_core * (0.40 * (wire[..., None] ** 2))
        )
        canvas = alpha_over(canvas, disc_rgb, disc_mask * 0.99)

        canvas = additive_glow(canvas, c_cyan * 0.5 + c_core * 0.5, (1.0 - smoothstep(0.005, 0.012, d_saw)) * 0.96)

        proj = (x + y) * 0.5
        s_pos = phase * 1.85 - 0.45
        shine = np.exp(-(((proj - s_pos) / 0.075) ** 2))
        canvas = additive_glow(canvas, c_core, shine * (r < 0.36) * 0.65)

        rgba = (np.clip(canvas, 0.0, 1.0) * 255.0).astype(np.uint8)
        return Image.fromarray(rgba, mode="RGBA")

    # -----------------------------------------------------------------------
    # CROSSHAIR: Crisp Cyber-Prism Precision Crosshair (+)
    # -----------------------------------------------------------------------
    if mode == "crosshair":
        cx, cy = 0.50, 0.50
        d_h = np.minimum(sd_segment(x, y, 0.14, cy, 0.39, cy), sd_segment(x, y, 0.61, cy, 0.86, cy))
        d_v = np.minimum(sd_segment(x, y, cx, 0.14, cx, 0.39), sd_segment(x, y, cx, 0.61, cx, 0.86))
        d_dot = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        d_struct = np.minimum(np.minimum(d_h, d_v), d_dot - 0.015)

        canvas = alpha_over(canvas, obsidian, (1.0 - smoothstep(0.014, 0.028, d_struct - 0.010)) * 0.99)
        fill = 1.0 - smoothstep(0.008, 0.015, d_struct)
        canvas = alpha_over(canvas, np.array([0.01, 0.03, 0.08], dtype=np.float32) + c_indigo * 0.4, fill * 0.99)
        bevel = 1.0 - smoothstep(0.004, 0.010, np.abs(d_struct - 0.010))
        canvas = additive_glow(canvas, c_cyan * 0.45 + c_core * 0.55, bevel * 0.98)

        proj = (x + y) * 0.5
        shine = np.exp(-(((proj - (phase * 1.85 - 0.45)) / 0.075) ** 2))
        canvas = additive_glow(canvas, c_core, shine * (d_struct < 0.020) * 0.85)
        return Image.fromarray((np.clip(canvas, 0.0, 1.0) * 255.0).astype(np.uint8), mode="RGBA")

    # -----------------------------------------------------------------------
    # RESIZE / MOVE / UPARROW / NO / PEN
    # -----------------------------------------------------------------------
    if mode in ("sizens", "sizewe", "sizenwse", "sizenesw", "sizeall", "uparrow", "pen"):
        if mode == "sizens":
            ang_r, two_way = 0.0, True
        elif mode == "sizewe":
            ang_r, two_way = math.pi / 2.0, True
        elif mode == "sizenwse":
            ang_r, two_way = -math.pi / 4.0, True
        elif mode == "sizenesw":
            ang_r, two_way = math.pi / 4.0, True
        elif mode == "uparrow":
            ang_r, two_way = 0.0, False
        elif mode == "pen":
            ang_r, two_way = -math.pi / 4.0, False
        else:
            ang_r, two_way = 0.0, True

        dx, dy = x - 0.50, y - 0.50
        ca, sa = math.cos(-ang_r), math.sin(-ang_r)
        rx = dx * ca - dy * sa + 0.50
        ry = dx * sa + dy * ca + 0.50

        if mode == "sizeall":
            d_shaft = np.minimum(sd_segment(x, y, 0.22, 0.50, 0.78, 0.50), sd_segment(x, y, 0.50, 0.22, 0.50, 0.78)) - 0.020
            heads = [
                [(0.50, 0.10), (0.37, 0.26), (0.63, 0.26)],
                [(0.50, 0.90), (0.37, 0.74), (0.63, 0.74)],
                [(0.10, 0.50), (0.26, 0.37), (0.26, 0.63)],
                [(0.90, 0.50), (0.74, 0.37), (0.74, 0.63)],
            ]
            sd_shape = d_shaft
            for h_pts in heads:
                sd_shape = np.minimum(sd_shape, sd_polygon(x, y, h_pts))
        elif mode == "pen":
            pen_pts = [(0.12, 0.12), (0.34, 0.22), (0.86, 0.74), (0.74, 0.86), (0.22, 0.34)]
            sd_shape = sd_polygon(x, y, pen_pts)
        elif two_way:
            d_shaft = sd_segment(rx, ry, 0.50, 0.24, 0.50, 0.76) - 0.022
            h_top = sd_polygon(rx, ry, [(0.50, 0.10), (0.35, 0.29), (0.65, 0.29)])
            h_bot = sd_polygon(rx, ry, [(0.50, 0.90), (0.35, 0.71), (0.65, 0.71)])
            sd_shape = np.minimum(d_shaft, np.minimum(h_top, h_bot))
        else:
            d_shaft = sd_segment(rx, ry, 0.50, 0.28, 0.50, 0.84) - 0.026
            h_top = sd_polygon(rx, ry, [(0.50, 0.10), (0.32, 0.34), (0.68, 0.34)])
            sd_shape = np.minimum(d_shaft, h_top)

        canvas = alpha_over(canvas, obsidian, (1.0 - smoothstep(0.014, 0.026, sd_shape)) * 0.99)
        body_a = 1.0 - smoothstep(-0.003, 0.004, sd_shape)
        wire, facet = crystalline_fractal_zoom(x, y, 0.50, 0.50, f_phase, theta)
        body_rgb = (
            np.array([0.01, 0.03, 0.08], dtype=np.float32)
            + c_indigo * (0.35 * facet[..., None])
            + c_violet * (0.78 * wire[..., None])
            + c_cyan * (0.52 * wire[..., None])
            + c_core * (0.40 * (wire[..., None] ** 2))
        )
        canvas = alpha_over(canvas, body_rgb, body_a * 0.99)
        edge_glow = 1.0 - smoothstep(0.006, 0.013, np.abs(sd_shape))
        canvas = additive_glow(canvas, c_cyan * 0.40 + c_core * 0.60, edge_glow * 0.99)

        proj = (x + y) * 0.5
        shine = np.exp(-(((proj - (phase * 1.85 - 0.45)) / 0.075) ** 2))
        canvas = additive_glow(canvas, c_core, shine * (sd_shape < 0.010) * 0.85)
        return Image.fromarray((np.clip(canvas, 0.0, 1.0) * 255.0).astype(np.uint8), mode="RGBA")

    if mode == "no":
        cx, cy = 0.50, 0.50
        r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        d_ring = np.abs(r - 0.30) - 0.032
        d_slash = sd_segment(x, y, 0.29, 0.29, 0.71, 0.71) - 0.028
        sd_shape = np.minimum(d_ring, d_slash)

        canvas = alpha_over(canvas, obsidian, (1.0 - smoothstep(0.014, 0.026, sd_shape)) * 0.99)
        body_a = 1.0 - smoothstep(-0.003, 0.004, sd_shape)
        c_warn = np.array([1.00, 0.24, 0.45], dtype=np.float32)
        canvas = alpha_over(canvas, np.array([0.08, 0.01, 0.03], dtype=np.float32) + c_warn * 0.35, body_a * 0.99)
        edge_glow = 1.0 - smoothstep(0.006, 0.013, np.abs(sd_shape))
        canvas = additive_glow(canvas, c_warn * 0.55 + c_core * 0.45, edge_glow * 0.99)
        proj = (x + y) * 0.5
        shine = np.exp(-(((proj - (phase * 1.85 - 0.45)) / 0.075) ** 2))
        canvas = additive_glow(canvas, c_core, shine * (sd_shape < 0.010) * 0.85)
        return Image.fromarray((np.clip(canvas, 0.0, 1.0) * 255.0).astype(np.uint8), mode="RGBA")

    # -----------------------------------------------------------------------
    # ARROW, HAND, & HELP: Crystalline Fractal Cathedral Zoom + Slow Shine
    # -----------------------------------------------------------------------
    if mode in ("arrow", "help"):
        verts = [
            (0.06, 0.06),
            (0.06, 0.72),
            (0.16, 0.60),
            (0.25, 0.54),
            (0.38, 0.85),
            (0.50, 0.80),
            (0.36, 0.49),
            (0.50, 0.53),
            (0.62, 0.45),
        ]
        core_cx, core_cy = 0.26, 0.41
    else:  # hand
        verts = [
            (0.06, 0.05),
            (0.11, 0.68),
            (0.21, 0.57),
            (0.29, 0.51),
            (0.43, 0.85),
            (0.54, 0.79),
            (0.39, 0.46),
            (0.53, 0.46),
            (0.64, 0.37),
        ]
        core_cx, core_cy = 0.29, 0.39

    sd_blade = sd_polygon(x, y, verts)

    # 1. Clean jet-black outer rim around blade
    halo_alpha = (1.0 - smoothstep(0.014, 0.026, sd_blade)) * 0.99
    canvas = alpha_over(canvas, obsidian, halo_alpha)

    # 2. CRYSTALLINE FRACTAL ZOOM INTERIOR
    body_alpha = 1.0 - smoothstep(-0.003, 0.004, sd_blade)
    wire, facet = crystalline_fractal_zoom(x, y, core_cx, core_cy, f_phase, theta)

    body_rgb = (
        np.array([0.01, 0.03, 0.08], dtype=np.float32)
        + c_indigo * (0.35 * facet[..., None])
        + c_violet * (0.78 * wire[..., None])
        + c_cyan * (0.52 * wire[..., None])
        + c_core * (0.40 * (wire[..., None] ** 2))
    )
    canvas = alpha_over(canvas, body_rgb, body_alpha * 0.99)

    # 3. Vector-sharp Ice-White + Electric-Cyan perimeter bevel
    edge_glow = 1.0 - smoothstep(0.006, 0.013, np.abs(sd_blade))
    canvas = additive_glow(canvas, c_cyan * 0.40 + c_core * 0.60, edge_glow * 0.99)

    # 4. Very slow, graceful Cyber-Prism shine sweep (~3.6s cycle)
    proj = (x - 0.04) * 0.707 + (y - 0.04) * 0.707
    shine_pos = phase * 1.85 - 0.45
    shine_band = np.exp(-(((proj - shine_pos) / 0.065) ** 2))
    canvas = additive_glow(canvas, c_core, shine_band * (sd_blade < 0.010) * 0.85)

    # Optional crisp '?' badge in bottom-right for Help cursor
    if mode == "help":
        qx, qy = 0.74, 0.72
        dx_q, dy_q = x - qx, y - qy
        rq = np.sqrt(dx_q * dx_q + dy_q * dy_q)
        d_q_arc = np.abs(rq - 0.09)
        q_mask = (dy_q < 0.02) | (dx_q > 0.0)
        d_q_arc = np.where(q_mask, d_q_arc, 1e9)
        d_q_stem = sd_segment(x, y, qx, qy + 0.07, qx, qy + 0.13)
        d_q_dot = np.sqrt((x - qx) ** 2 + (y - (qy + 0.19)) ** 2)
        d_q = np.minimum(d_q_arc, np.minimum(d_q_stem, d_q_dot))
        canvas = alpha_over(canvas, obsidian, (1.0 - smoothstep(0.022, 0.044, d_q)) * 0.99)
        canvas = additive_glow(canvas, c_cyan * 0.45 + c_core * 0.55, (1.0 - smoothstep(0.010, 0.020, d_q)) * 0.98)

    rgba = (np.clip(canvas, 0.0, 1.0) * 255.0).astype(np.uint8)
    return Image.fromarray(rgba, mode="RGBA")


def save_transparent_gif(frames: list[Image.Image], path: str, duration_ms: int = 28):
    gif_frames = []
    for im in frames:
        rgba = np.array(im)
        alpha = rgba[..., 3]
        rgb_im = Image.fromarray(rgba[..., :3]).quantize(
            colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
        )
        pal = rgb_im.getpalette()
        pal = pal[: 255 * 3] + [0, 0, 0] * (256 - len(pal) // 3)
        arr = np.array(rgb_im, dtype=np.uint8)
        arr[alpha < 48] = 255
        out_im = Image.fromarray(arr, mode="P")
        out_im.putpalette(pal)
        out_im.info["transparency"] = 255
        gif_frames.append(out_im)

    gif_frames[0].save(
        path,
        save_all=True,
        append_images=gif_frames[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
        transparency=255,
    )


def build_cur_bytes(im: Image.Image, hotspot_x: int, hotspot_y: int) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    png_data = buf.getvalue()
    w, h = im.size
    wb = w if w < 256 else 0
    hb = h if h < 256 else 0

    icondir = struct.pack("<HHH", 0, 2, 1)
    entry = struct.pack("<BBBBHHII", wb, hb, 0, 0, hotspot_x, hotspot_y, len(png_data), 22)
    return icondir + entry + png_data


def save_ani(frames: list[Image.Image], path: str, hotspot_x: int, hotspot_y: int, jif_rate: int = 2):
    n = len(frames)
    anih_data = struct.pack("<9I", 36, n, n, 0, 0, 0, 0, jif_rate, 1)
    anih_chunk = b"anih" + struct.pack("<I", len(anih_data)) + anih_data

    icon_chunks = bytearray()
    for im in frames:
        cur = build_cur_bytes(im, hotspot_x, hotspot_y)
        icon_chunks += b"icon" + struct.pack("<I", len(cur)) + cur
        if len(cur) % 2 == 1:
            icon_chunks += b"\x00"

    fram_body = b"fram" + bytes(icon_chunks)
    list_chunk = b"LIST" + struct.pack("<I", len(fram_body)) + fram_body

    acon_body = b"ACON" + anih_chunk + list_chunk
    riff = b"RIFF" + struct.pack("<I", len(acon_body)) + acon_body

    with open(path, "wb") as f:
        f.write(riff)


def save_contrast_preview(all_hi: dict, out_path: str):
    w, h = 680, 220
    n = len(all_hi["arrow"])
    modes = ["arrow", "hand", "ibeam", "busy"]
    preview_frames = []
    for i in range(n):
        img = Image.new("RGB", (w, h), (255, 255, 255))
        img.paste(Image.new("RGB", (w // 2, h), (8, 10, 16)), (w // 2, 0))
        for col_offset in (0, w // 2):
            for idx, m in enumerate(modes):
                im = all_hi[m][i].resize((76, 76), Image.Resampling.LANCZOS)
                img.paste(im, (col_offset + 12 + idx * 80, 72), im)
        preview_frames.append(img)

    preview_frames[0].save(
        out_path,
        save_all=True,
        append_images=preview_frames[1:],
        duration=28,
        loop=0,
    )


def add_holographic_split_prism(im: Image.Image, phase: float) -> Image.Image:
    """
    Add a tight 1px Holographic Split-Prism Border (electric cyan shifted top-left,
    electric violet shifted bottom-right) just outside the cursor's black border.
    """
    arr = np.array(im, dtype=np.float32) / 255.0
    h, w, _ = arr.shape
    a = arr[..., 3]
    sh = max(1, round(w / 48.0))  # ~1px at 64x64, ~5px at 256x256

    a_ul = np.zeros_like(a)
    a_ul[:-sh, :-sh] = a[sh:, sh:]

    a_dr = np.zeros_like(a)
    a_dr[sh:, sh:] = a[:-sh, :-sh]

    outside = np.clip(1.0 - a * 1.25, 0.0, 1.0)
    shimmer = 0.72 + 0.28 * math.sin(phase * 2.0 * math.pi)

    m_cyan = np.clip(a_ul * outside * shimmer, 0.0, 1.0)
    m_violet = np.clip(a_dr * outside * shimmer, 0.0, 1.0)

    c_cyan = np.array([0.00, 0.94, 1.00], dtype=np.float32)
    c_violet = np.array([0.68, 0.22, 1.00], dtype=np.float32)

    prism_rgb = c_cyan * m_cyan[..., None] + c_violet * m_violet[..., None]
    prism_a = np.clip(np.maximum(m_cyan, m_violet) * 0.90, 0.0, 1.0)

    # Composite prism edge behind the main cursor
    out_a = a + prism_a * (1.0 - a)
    out_rgb = arr[..., :3] * a[..., None] + prism_rgb * (1.0 - a[..., None])
    out_rgb = np.where(out_a[..., None] > 1e-5, out_rgb / np.maximum(out_a[..., None], 1e-5), 0.0)

    out = np.concatenate([np.clip(out_rgb, 0.0, 1.0), np.clip(out_a, 0.0, 1.0)[..., None]], axis=-1)
    return Image.fromarray((out * 255.0).astype(np.uint8), mode="RGBA")


def main():
    n_frames = 108  # ~3.6s loop so the shine sweeps very slowly while fractal stays crisp!
    # High-DPI 64x64 hotspots (2x supersampled from 128x128 for crispness without upscaling blur)
    variants = [
        ("arrow", (4, 4)),
        ("hand", (4, 4)),
        ("help", (4, 4)),
        ("pen", (8, 8)),
        ("ibeam", (32, 32)),
        ("busy", (32, 32)),
        ("crosshair", (32, 32)),
        ("sizens", (32, 32)),
        ("sizewe", (32, 32)),
        ("sizenwse", (32, 32)),
        ("sizenesw", (32, 32)),
        ("sizeall", (32, 32)),
        ("uparrow", (32, 6)),
        ("no", (32, 32)),
    ]

    sharpen = ImageFilter.UnsharpMask(radius=0.5, percent=65, threshold=2)

    all_hi = {}
    for mode, (hx, hy) in variants:
        print(f"Rendering {mode} ({n_frames} frames)...")
        hi_frames = [
            render_violent_prism_frame(256, i, n_frames, mode=mode)
            for i in range(n_frames)
        ]
        # Render 128x128 (2x supersampled) -> 64x64 + light crisp unsharp mask
        ss_frames = [
            render_violent_prism_frame(128, i, n_frames, mode=mode)
            for i in range(n_frames)
        ]
        cur_frames = [
            im.resize((64, 64), Image.Resampling.LANCZOS).filter(sharpen)
            for im in ss_frames
        ]
        if mode in ("arrow", "hand", "ibeam", "busy"):
            all_hi[mode] = hi_frames
            gif_hi_path = os.path.join(OUT_DIR, f"cyber_prism_{mode}_256.gif")
            gif_64_path = os.path.join(OUT_DIR, f"cyber_prism_{mode}_64.gif")
            save_transparent_gif(hi_frames, gif_hi_path, duration_ms=28)
            save_transparent_gif(cur_frames, gif_64_path, duration_ms=28)

        ani_path = os.path.join(OUT_DIR, f"cyber_prism_{mode}.ani")
        save_ani(cur_frames, ani_path, hotspot_x=hx, hotspot_y=hy, jif_rate=2)
        print(f"  Saved: {os.path.basename(ani_path)}")

    preview_path = os.path.join(OUT_DIR, "preview_light_and_dark.gif")
    save_contrast_preview(all_hi, preview_path)
    Image.open(preview_path).convert("RGB").save(os.path.join(OUT_DIR, "preview_frame0.png"))
    print(f"Saved contrast preview: {preview_path}")


if __name__ == "__main__":
    main()
