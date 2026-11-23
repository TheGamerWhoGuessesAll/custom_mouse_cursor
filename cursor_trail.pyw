import os
import sys
import io
import time
import math
import wave
import struct
import random
import winsound
import ctypes
from ctypes import wintypes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PID_PATH = os.path.join(BASE_DIR, "trail.pid")
LOG_PATH = os.path.join(BASE_DIR, "trail.log")

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
gdiplus = ctypes.WinDLL("gdiplus", use_last_error=True)

WS_POPUP = 0x80000000
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

ULW_ALPHA = 0x00000002
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01
DIB_RGB_COLORS = 0
SW_SHOWNOACTIVATE = 4
HWND_TOPMOST = -1
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
PM_REMOVE = 0x0001

WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HICON),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hCursor", wintypes.HANDLE),
        ("ptScreenPos", POINT),
    ]


CURSOR_SHOWING = 0x00000001


class SIZE(ctypes.Structure):
    _fields_ = [("cx", wintypes.LONG), ("cy", wintypes.LONG)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_ubyte),
        ("BlendFlags", ctypes.c_ubyte),
        ("SourceConstantAlpha", ctypes.c_ubyte),
        ("AlphaFormat", ctypes.c_ubyte),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]


class GdiplusStartupInput(ctypes.Structure):
    _fields_ = [
        ("GdiplusVersion", wintypes.UINT),
        ("DebugEventCallback", ctypes.c_void_p),
        ("SuppressBackgroundThread", wintypes.BOOL),
        ("SuppressExternalCodecs", wintypes.BOOL),
    ]


# Explicit 64-bit Win32 signatures
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = wintypes.ATOM
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT
]
user32.SetWindowPos.restype = wintypes.BOOL
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]
user32.GetCursorInfo.restype = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
user32.PeekMessageW.restype = wintypes.BOOL
user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND, wintypes.HDC, ctypes.POINTER(POINT), ctypes.POINTER(SIZE),
    wintypes.HDC, ctypes.POINTER(POINT), wintypes.COLORREF, ctypes.POINTER(BLENDFUNCTION), wintypes.DWORD,
]
user32.UpdateLayeredWindow.restype = wintypes.BOOL

gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC, ctypes.POINTER(BITMAPINFO), wintypes.UINT,
    ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD,
]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE

# GDI+ signatures
gdiplus.GdiplusStartup.argtypes = [ctypes.POINTER(ctypes.c_ulonglong), ctypes.POINTER(GdiplusStartupInput), ctypes.c_void_p]
gdiplus.GdiplusStartup.restype = ctypes.c_int
gdiplus.GdiplusShutdown.argtypes = [ctypes.c_ulonglong]
gdiplus.GdipCreateFromHDC.argtypes = [wintypes.HDC, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipCreateFromHDC.restype = ctypes.c_int
gdiplus.GdipDeleteGraphics.argtypes = [ctypes.c_void_p]
gdiplus.GdipSetSmoothingMode.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdiplus.GdipCreatePen1.argtypes = [wintypes.DWORD, ctypes.c_float, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipSetPenDashStyle.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdiplus.GdipDeletePen.argtypes = [ctypes.c_void_p]
gdiplus.GdipDrawLine.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float]
gdiplus.GdipDrawEllipse.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float]
gdiplus.GdipCreateSolidFill.argtypes = [wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipDeleteBrush.argtypes = [ctypes.c_void_p]
gdiplus.GdipFillEllipse.argtypes = [wintypes.HDC if False else ctypes.c_void_p, ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float]
gdiplus.GdipFillRectangle.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float]


@WNDPROC
def wnd_proc(hwnd, msg, wparam, lparam):
    if msg == 0x0010:
        user32.DestroyWindow(hwnd)
        return 0
    if msg == 0x0002:
        user32.PostQuitMessage(0)
        return 0
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


def create_overlay_window():
    hinst = kernel32.GetModuleHandleW(None)
    cls_name = "CyberPrismNeuralTrailOverlay"
    wc = WNDCLASSEXW()
    wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
    wc.lpfnWndProc = wnd_proc
    wc.hInstance = hinst
    wc.lpszClassName = cls_name
    user32.RegisterClassExW(ctypes.byref(wc))

    ex_style = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    hwnd = user32.CreateWindowExW(
        ex_style, cls_name, "CyberPrismNeuralTrail", WS_POPUP,
        0, 0, 16, 16, None, None, hinst, None
    )
    user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
    return hwnd


def argb(a: int, r: int, g: int, b: int) -> int:
    return ((a & 0xFF) << 24) | ((r & 0xFF) << 16) | ((g & 0xFF) << 8) | (b & 0xFF)


def make_cyber_click_wav(base_freq: float, hi_freq: float, duration_s: float, volume: float = 0.95) -> bytes:
    """Synthesize a crisp, loud high-tech crystal/mechanical click .wav."""
    sr = 44100
    n_samples = int(sr * duration_s)
    buf = io.BytesIO()
    rng = random.Random(42)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for i in range(n_samples):
            t_s = i / sr
            t = i / n_samples
            # Punchy 2ms percussive snap + clean glassy harmonic ping
            snap = (rng.uniform(-1.0, 1.0)) * math.exp(-t_s * 750.0) * 0.90
            ping = (
                0.55 * math.sin(2.0 * math.pi * base_freq * t_s)
                + 0.30 * math.sin(2.0 * math.pi * hi_freq * t_s)
                + 0.25 * math.sin(2.0 * math.pi * (base_freq * 0.5) * t_s)
            ) * math.exp(-t * 7.5)
            attack = min(1.0, i / 8.0)
            sample = max(-1.0, min(1.0, (snap + ping) * attack * volume))
            val = int(sample * 32767)
            frames += struct.pack("<h", val)
        wf.writeframes(bytes(frames))
    return buf.getvalue()


def render_effects(hwnd, ripples, laser_pts, now: float, max_ripple_age: float = 0.38, max_laser_age: float = 0.26):
    xs = [r[0] for r in ripples] + [p[0] for p in laser_pts]
    ys = [r[1] for r in ripples] + [p[1] for p in laser_pts]
    pad = 52
    left = int(min(xs)) - pad
    top = int(min(ys)) - pad
    w = max(16, min(1400, int(max(xs)) + pad - left))
    h = max(16, min(1400, int(max(ys)) + pad - top))

    # Re-assert HWND_TOPMOST so clicking Chrome or opening new apps never pushes the overlay behind
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)

    screen_dc = user32.GetDC(None)
    mem_dc = gdi32.CreateCompatibleDC(screen_dc)

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0

    bits_ptr = ctypes.c_void_p()
    hbmp = gdi32.CreateDIBSection(mem_dc, ctypes.byref(bmi), DIB_RGB_COLORS, ctypes.byref(bits_ptr), None, 0)
    old_bmp = gdi32.SelectObject(mem_dc, hbmp)
    ctypes.memset(bits_ptr, 0, w * h * 4)

    gfx = ctypes.c_void_p()
    gdiplus.GdipCreateFromHDC(mem_dc, ctypes.byref(gfx))
    gdiplus.GdipSetSmoothingMode(gfx, 4)  # AntiAlias

    pen = ctypes.c_void_p()
    brush = ctypes.c_void_p()

    # 0. Laser Targeter / Crisp Dashed-Dotted Tracking Line
    if len(laser_pts) >= 2:
        for i in range(len(laser_pts) - 1):
            x0, y0, t0 = laser_pts[i]
            x1, y1, t1 = laser_pts[i + 1]
            life = max(0.0, 1.0 - (now - 0.5 * (t0 + t1)) / max_laser_age)
            a_glow = int(95 * life)
            a_core = int(230 * life)
            if a_core < 10:
                continue
            if a_glow > 6:
                gdiplus.GdipCreatePen1(argb(a_glow, 0, 210, 255), ctypes.c_float(3.6), 2, ctypes.byref(pen))
                gdiplus.GdipSetPenDashStyle(pen, 2)  # DashStyleDot
                gdiplus.GdipDrawLine(gfx, pen, ctypes.c_float(x0 - left), ctypes.c_float(y0 - top), ctypes.c_float(x1 - left), ctypes.c_float(y1 - top))
                gdiplus.GdipDeletePen(pen)
            gdiplus.GdipCreatePen1(argb(a_core, 160, 248, 255), ctypes.c_float(1.6), 2, ctypes.byref(pen))
            gdiplus.GdipSetPenDashStyle(pen, 2)  # DashStyleDot
            gdiplus.GdipDrawLine(gfx, pen, ctypes.c_float(x0 - left), ctypes.c_float(y0 - top), ctypes.c_float(x1 - left), ctypes.c_float(y1 - top))
            gdiplus.GdipDeletePen(pen)

    # CursorFX-style Neon Click Ripples + Radial Burst
    for rx, ry, (cr, cg, cb), born in ripples:
        t = (now - born) / max_ripple_age
        if t >= 1.0:
            continue
        ease = 1.0 - (1.0 - t) ** 2.6
        fade = (1.0 - t) ** 1.15
        lx, ly = rx - left, ry - top

        # 1. Instant bright core flash on click (first 35% of animation)
        if t < 0.35:
            cf = 1.0 - t / 0.35
            r_flash = 3.0 + 7.0 * (1.0 - cf)
            gdiplus.GdipCreateSolidFill(argb(int(180 * cf), 235, 252, 255), ctypes.byref(brush))
            gdiplus.GdipFillEllipse(gfx, brush, ctypes.c_float(lx - r_flash), ctypes.c_float(ly - r_flash), ctypes.c_float(r_flash * 2), ctypes.c_float(r_flash * 2))
            gdiplus.GdipDeleteBrush(brush)

        # 2. Primary glowing shockwave ring (outer soft glow + crisp bright ring)
        rad1 = 4.0 + 34.0 * ease
        a1_glow = int(110 * fade)
        a1_core = int(245 * fade)
        if a1_glow > 6:
            gdiplus.GdipCreatePen1(argb(a1_glow, cr, cg, cb), ctypes.c_float(4.5), 2, ctypes.byref(pen))
            gdiplus.GdipDrawEllipse(gfx, pen, ctypes.c_float(lx - rad1), ctypes.c_float(ly - rad1), ctypes.c_float(rad1 * 2), ctypes.c_float(rad1 * 2))
            gdiplus.GdipDeletePen(pen)
        if a1_core > 6:
            gdiplus.GdipCreatePen1(argb(a1_core, 225, 250, 255), ctypes.c_float(1.6), 2, ctypes.byref(pen))
            gdiplus.GdipDrawEllipse(gfx, pen, ctypes.c_float(lx - rad1), ctypes.c_float(ly - rad1), ctypes.c_float(rad1 * 2), ctypes.c_float(rad1 * 2))
            gdiplus.GdipDeletePen(pen)

        # 3. Staggered secondary inner ripple ring
        if t > 0.10:
            t2 = (t - 0.10) / 0.90
            ease2 = 1.0 - (1.0 - t2) ** 2.4
            fade2 = (1.0 - t2) ** 1.3
            rad2 = 3.0 + 24.0 * ease2
            a2 = int(200 * fade2)
            if a2 > 6:
                gdiplus.GdipCreatePen1(argb(a2, cr, cg, cb), ctypes.c_float(1.4), 2, ctypes.byref(pen))
                gdiplus.GdipDrawEllipse(gfx, pen, ctypes.c_float(lx - rad2), ctypes.c_float(ly - rad2), ctypes.c_float(rad2 * 2), ctypes.c_float(rad2 * 2))
                gdiplus.GdipDeletePen(pen)

        # 4. 8 crisp radial neon burst rays shooting outward
        ray_a = int(220 * ((1.0 - t) ** 1.4))
        if ray_a > 8:
            r_in = 5.0 + 22.0 * ease
            r_out = r_in + 7.5 * (1.0 - t)
            gdiplus.GdipCreatePen1(argb(ray_a, 220, 250, 255), ctypes.c_float(1.3), 2, ctypes.byref(pen))
            for k in range(8):
                ang = k * (math.pi / 4.0)
                ca, sa = math.cos(ang), math.sin(ang)
                gdiplus.GdipDrawLine(
                    gfx, pen,
                    ctypes.c_float(lx + ca * r_in), ctypes.c_float(ly + sa * r_in),
                    ctypes.c_float(lx + ca * r_out), ctypes.c_float(ly + sa * r_out),
                )
            gdiplus.GdipDeletePen(pen)

    gdiplus.GdipDeleteGraphics(gfx)

    dst_pt = POINT(left, top)
    wnd_sz = SIZE(w, h)
    src_pt = POINT(0, 0)
    blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
    ulw_ok = user32.UpdateLayeredWindow(
        hwnd, screen_dc, ctypes.byref(dst_pt), ctypes.byref(wnd_sz),
        mem_dc, ctypes.byref(src_pt), 0, ctypes.byref(blend), ULW_ALPHA
    )
    if not ulw_ok:
        err = ctypes.get_last_error()
        with open(LOG_PATH, "a", encoding="utf-8") as lf:
            lf.write(f"UpdateLayeredWindow failed: err={err}, w={w}, h={h}\n")

    gdi32.SelectObject(mem_dc, old_bmp)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(None, screen_dc)


def clear_overlay(hwnd):
    screen_dc = user32.GetDC(None)
    mem_dc = gdi32.CreateCompatibleDC(screen_dc)
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = 4
    bmi.bmiHeader.biHeight = -4
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bits_ptr = ctypes.c_void_p()
    hbmp = gdi32.CreateDIBSection(mem_dc, ctypes.byref(bmi), DIB_RGB_COLORS, ctypes.byref(bits_ptr), None, 0)
    old_bmp = gdi32.SelectObject(mem_dc, hbmp)
    ctypes.memset(bits_ptr, 0, 64)
    dst_pt = POINT(0, 0)
    wnd_sz = SIZE(4, 4)
    src_pt = POINT(0, 0)
    blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
    user32.UpdateLayeredWindow(hwnd, screen_dc, ctypes.byref(dst_pt), ctypes.byref(wnd_sz), mem_dc, ctypes.byref(src_pt), 0, ctypes.byref(blend), ULW_ALPHA)
    gdi32.SelectObject(mem_dc, old_bmp)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(None, screen_dc)


def main():
    with open(PID_PATH, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))

    gp_token = ctypes.c_ulonglong()
    gp_in = GdiplusStartupInput(1, None, False, False)
    gdiplus.GdiplusStartup(ctypes.byref(gp_token), ctypes.byref(gp_in), None)

    hwnd = create_overlay_window()
    msg = wintypes.MSG()
    pt = POINT()
    ci = CURSORINFO()
    ci.cbSize = ctypes.sizeof(CURSORINFO)
    wav_left_path = os.path.join(BASE_DIR, "click_left.wav")
    wav_right_path = os.path.join(BASE_DIR, "click_right.wav")
    with open(wav_left_path, "wb") as wf:
        wf.write(make_cyber_click_wav(2600.0, 5200.0, 0.036, volume=0.95))
    with open(wav_right_path, "wb") as wf:
        wf.write(make_cyber_click_wav(1850.0, 3700.0, 0.044, volume=0.95))

    ripples = []     # [x, y, (r, g, b), born_time]
    laser_pts = []   # [x, y, born_time]
    max_ripple_age = 0.38
    max_laser_age = 0.26
    was_l = False
    was_r = False
    cleared = True

    try:
        while True:
            while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                if msg.message == 0x0012:
                    return
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

            now = time.perf_counter()

            # Hide/skip ONLY when GetCursorInfo succeeds AND cursor is explicitly hidden (in-game)
            ci.cbSize = ctypes.sizeof(CURSORINFO)
            ok_ci = user32.GetCursorInfo(ctypes.byref(ci))
            if ok_ci and not (ci.flags & CURSOR_SHOWING):
                ripples.clear()
                laser_pts.clear()
                was_l = False
                was_r = False
                if not cleared:
                    clear_overlay(hwnd)
                    cleared = True
                time.sleep(0.04)
                continue

            l_down = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
            r_down = bool(user32.GetAsyncKeyState(0x02) & 0x8000)

            has_pos = bool(user32.GetCursorPos(ctypes.byref(pt)))
            if has_pos:
                mx, my = float(pt.x), float(pt.y)
                if not laser_pts or math.hypot(mx - laser_pts[-1][0], my - laser_pts[-1][1]) >= 4.0:
                    laser_pts.append([mx, my, now])
                    if len(laser_pts) > 18:
                        laser_pts = laser_pts[-18:]

            if l_down and not was_l:
                winsound.PlaySound(wav_left_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                if has_pos:
                    ripples.append([float(pt.x), float(pt.y), (0, 234, 255), now])
            if r_down and not was_r:
                winsound.PlaySound(wav_right_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                if has_pos:
                    ripples.append([float(pt.x), float(pt.y), (157, 107, 255), now])

            if len(ripples) > 10:
                ripples = ripples[-10:]
            was_l = l_down
            was_r = r_down

            ripples = [r for r in ripples if (now - r[3]) <= max_ripple_age]
            laser_pts = [p for p in laser_pts if (now - p[2]) <= max_laser_age]

            if ripples or len(laser_pts) >= 2:
                render_effects(hwnd, ripples, laser_pts, now, max_ripple_age=max_ripple_age, max_laser_age=max_laser_age)
                cleared = False
                time.sleep(0.014)  # ~60+ FPS, ultra low CPU via GDI+
            else:
                if not cleared:
                    clear_overlay(hwnd)
                    cleared = True
                time.sleep(0.025)
    except Exception:
        import traceback
        with open(LOG_PATH, "w", encoding="utf-8") as lf:
            traceback.print_exc(file=lf)
    finally:
        gdiplus.GdiplusShutdown(gp_token)
        if os.path.exists(PID_PATH):
            try:
                os.remove(PID_PATH)
            except OSError:
                pass


if __name__ == "__main__":
    main()
