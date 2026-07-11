"""
╔══════════════════════════════════════════════════════════════════╗
║         SARA AI — Ultra Interface v3.0  (2026 Edition)          ║
║         Premium Futuristic Desktop AI Operating System          ║
╚══════════════════════════════════════════════════════════════════╝
Requirements:
    pip install customtkinter pillow
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import font as tkfont
import threading
import time
import math
import random
import colorsys

# ── Stub imports for standalone demo ──────────────────────────────────────────
try:
    from speech.stt import listen
except ImportError:
    def listen(timeout=8, phrase_time_limit=12, stop_event=None):
        time.sleep(2)
        return "Hello SARA, can you help me analyze some data?"

try:
    from speech.tts import speak_response, speak_smart, stop_speech
except ImportError:
    def speak_smart(text): print(f"[TTS] {text}")
    def speak_response(text, on_start=None, on_done=None, on_error=None):
        if on_start:
            on_start()
        print(f"[TTS] {text}")
        if on_done:
            on_done()
    def stop_speech(): pass

try:
    from ai.brain import ask_ai
except ImportError:
    def ask_ai(text):
        time.sleep(1.2)
        responses = [
            "I've analyzed your request and identified 3 optimal pathways. The most efficient solution involves restructuring the data pipeline with async processing.",
            "Based on my neural analysis, I recommend the following approach: First, establish a baseline metric. Then iterate using gradient descent optimization.",
            "Understood. Processing complete. I've cross-referenced 847 data points and the probability matrix suggests a 94.3% confidence interval.",
            "Fascinating query. Let me synthesize the available information streams and compile a comprehensive response for your review.",
        ]
        return random.choice(responses)

try:
    from wake_word import wait_for_wake_word
except ImportError:
    def wait_for_wake_word(): time.sleep(3)


# ══════════════════════════════════════════════════════════════════════════════
#  DESIGN TOKENS
# ══════════════════════════════════════════════════════════════════════════════

# ── Background layers ──
BG_VOID        = "#030510"   # deepest background
BG_BASE        = "#050816"   # main bg
BG_SURFACE     = "#080d1a"   # panel base
BG_ELEVATED    = "#0b1120"   # elevated card
BG_GLASS       = "#0d1528"   # glassmorphism panel
BG_INPUT       = "#060b17"   # input field

# ── Neon accents ──
CYAN           = "#00D4FF"
CYAN_DIM       = "#00a8cc"
CYAN_GHOST     = "#00d4ff18"
PURPLE         = "#A855F7"
PURPLE_DIM     = "#7c3aed"
PURPLE_GHOST   = "#a855f718"
INDIGO         = "#6366f1"
VIOLET         = "#8b5cf6"
PINK           = "#ec4899"

# ── AI bubble palette ──
AI_BG          = "#06131f"
AI_BG2         = "#081928"
AI_BORDER      = "#0e3a52"
AI_GLOW        = "#00d4ff22"
AI_NAME        = "#00D4FF"
AI_TEXT        = "#a8d8ea"
AI_TEXT2       = "#7ec8e3"

# ── User bubble palette ──
USR_BG         = "#0f0820"
USR_BG2        = "#150b2e"
USR_BORDER     = "#2d1060"
USR_GLOW       = "#a855f722"
USR_NAME       = "#c084fc"
USR_TEXT       = "#ddd6fe"
USR_TEXT2      = "#c4b5fd"

# ── Neutral text ──
TEXT_HI        = "#e2e8f0"
TEXT_MED       = "#94a3b8"
TEXT_LO        = "#475569"
TEXT_GHOST     = "#1e293b"

# ── Status colors ──
GREEN          = "#10b981"
AMBER          = "#f59e0b"
RED            = "#ef4444"

# ── Borders ──
BD_SUBTLE      = "#0f1e35"
BD_DIM         = "#162035"
BD_MED         = "#1e3a5f"

# ── Fonts — JetBrains Mono for the terminal/data feel, Segoe UI Variable for prose ──
def _ff(*names):
    """Return first available font family."""
    avail = set(tk.font.families() if tk.font else [])
    for n in names:
        if n in avail:
            return n
    return names[-1]

_MONO  = None   # resolved at startup
_SANS  = None


def resolve_fonts():
    global _MONO, _SANS
    _MONO = _ff("JetBrains Mono", "Cascadia Code", "Fira Code", "Consolas", "Courier New")
    _SANS = _ff("Segoe UI Variable", "Segoe UI", "Poppins", "SF Pro Display",
                "Helvetica Neue", "Arial")


# ── Named font specs (resolved after Tk is up) ──
def F(family, size, weight="normal"):
    return (family, size, weight)


# ══════════════════════════════════════════════════════════════════════════════
#  UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def hex_blend(c1: str, c2: str, t: float) -> str:
    """Linear interpolate between two hex colors."""
    r1, g1, b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
    r2, g2, b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
    r = int(r1 + (r2-r1)*t)
    g = int(g1 + (g2-g1)*t)
    b = int(b1 + (b2-b1)*t)
    return f"#{r:02x}{g:02x}{b:02x}"


# ══════════════════════════════════════════════════════════════════════════════
#  REUSABLE WIDGET: GLASS FRAME
# ══════════════════════════════════════════════════════════════════════════════

class GlassFrame(ctk.CTkFrame):
    """A frame with glass-like dark styling and optional neon border."""

    def __init__(self, parent, glow_color=None, border_color=BD_DIM,
                 radius=16, **kw):
        kw.setdefault("fg_color", BG_GLASS)
        kw.setdefault("corner_radius", radius)
        kw.setdefault("border_width", 1)
        kw.setdefault("border_color", border_color)
        super().__init__(parent, **kw)


# ══════════════════════════════════════════════════════════════════════════════
#  WIDGET: NEON CANVAS SEPARATOR
# ══════════════════════════════════════════════════════════════════════════════

class NeonSep(tk.Canvas):
    def __init__(self, parent, color=CYAN, height=1, **kw):
        super().__init__(parent, height=height+4, bg=BG_SURFACE,
                         highlightthickness=0, **kw)
        self.color = color
        self.bind("<Configure>", self._draw)

    def _draw(self, e=None):
        self.delete("all")
        w = self.winfo_width()
        self.create_line(0, 2, w, 2, fill=self.color, width=1)


# ══════════════════════════════════════════════════════════════════════════════
#  WIDGET: TYPING INDICATOR
# ══════════════════════════════════════════════════════════════════════════════

class TypingIndicator(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self._dots = []
        self._phase = 0
        self._job = None

        wrapper = GlassFrame(self, border_color=AI_BORDER, radius=14,
                             fg_color=AI_BG)
        wrapper.pack(anchor="w", padx=(16, 80), pady=4)

        icon = ctk.CTkLabel(wrapper, text="◈",
                            font=F(_MONO, 11),
                            text_color=CYAN, width=24)
        icon.pack(side="left", padx=(10, 6), pady=10)

        dot_row = ctk.CTkFrame(wrapper, fg_color="transparent")
        dot_row.pack(side="left", padx=(0, 14), pady=10)

        for _ in range(3):
            d = ctk.CTkLabel(dot_row, text="●",
                             font=F(_MONO, 9), text_color=TEXT_LO)
            d.pack(side="left", padx=3)
            self._dots.append(d)

        self._animate()

    def _animate(self):
        colors = [TEXT_LO, TEXT_LO, TEXT_LO]
        i = self._phase % 3
        colors[i] = CYAN
        if i > 0: colors[i-1] = AI_TEXT2
        for d, c in zip(self._dots, colors):
            d.configure(text_color=c)
        self._phase += 1
        self._job = self.after(380, self._animate)

    def destroy(self):
        if self._job:
            try: self.after_cancel(self._job)
            except: pass
        super().destroy()


# ══════════════════════════════════════════════════════════════════════════════
#  WIDGET: CHAT BUBBLE
# ══════════════════════════════════════════════════════════════════════════════

class ChatBubble(ctk.CTkFrame):
    """
    Premium two-sided chat bubble.
    is_ai=True  → left, cyan glass
    is_ai=False → right, indigo glass
    Fade-in animation on appearance.
    """

    def __init__(self, parent, sender: str, text: str,
                 is_ai: bool = True, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self._alpha = 0.0
        self.is_ai = is_ai
        self.grid_columnconfigure(0, weight=1)

        self._build(sender, text, is_ai)
        self._fade_in()

    def _build(self, sender, text, is_ai):
        # Layout parameters
        if is_ai:
            pad_l, pad_r = 14, 90
            anchor = "w"
            bg      = AI_BG
            border  = AI_BORDER
            name_c  = AI_NAME
            text_c  = AI_TEXT
            icon    = "◈"
            icon_c  = CYAN
            bar_c   = CYAN
            bar_side = "left"
            ts_anchor = "w"
        else:
            pad_l, pad_r = 90, 14
            anchor = "e"
            bg      = USR_BG
            border  = USR_BORDER
            name_c  = USR_NAME
            text_c  = USR_TEXT
            icon    = "◉"
            icon_c  = PURPLE
            bar_c   = PURPLE
            bar_side = "right"
            ts_anchor = "e"

        # Outer alignment container
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="x", padx=(pad_l, pad_r), pady=(2, 0))

        # ── Name + icon row ──
        meta_row = ctk.CTkFrame(outer, fg_color="transparent")
        meta_row.pack(fill="x", pady=(0, 3))

        icon_lbl = ctk.CTkLabel(meta_row, text=icon,
                                font=F(_MONO, 12),
                                text_color=icon_c, width=22)
        name_lbl = ctk.CTkLabel(meta_row, text=sender.upper(),
                                font=F(_MONO, 9, "bold"),
                                text_color=name_c)

        if is_ai:
            icon_lbl.pack(side="left", padx=(0, 5))
            name_lbl.pack(side="left")
        else:
            name_lbl.pack(side="right")
            icon_lbl.pack(side="right", padx=(5, 0))

        # ── Bubble card ──
        card = ctk.CTkFrame(outer, fg_color=bg, corner_radius=14,
                            border_width=1, border_color=border)
        card.pack(fill="none", anchor=anchor)
        card.grid_columnconfigure(1 if is_ai else 0, weight=1)

        # Neon accent bar
        accent = ctk.CTkFrame(card, fg_color=bar_c, width=3,
                              corner_radius=2)
        if bar_side == "left":
            accent.grid(row=0, column=0, sticky="ns", padx=(5, 0), pady=10)
        else:
            accent.grid(row=0, column=2, sticky="ns", padx=(0, 5), pady=10)

        # Message text
        col = 1
        msg = ctk.CTkLabel(card, text=text,
                           font=F(_SANS, 12),
                           text_color=text_c,
                           wraplength=520,
                           justify="left" if is_ai else "right",
                           anchor="w" if is_ai else "e")
        msg.grid(row=0, column=col, padx=(8, 12) if is_ai else (12, 8),
                 pady=(12, 12), sticky="ew")

        # ── Timestamp ──
        ts = ctk.CTkLabel(outer,
                          text=time.strftime("%I:%M %p"),
                          font=F(_MONO, 8),
                          text_color=TEXT_LO)
        ts.pack(anchor=ts_anchor, padx=4, pady=(2, 6))

    def _fade_in(self):
        """Simulate fade-in by gradually revealing (limited in Tkinter)."""
        # We use a subtle slide-in feel via after scheduling
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  WIDGET: SYSTEM MESSAGE
# ══════════════════════════════════════════════════════════════════════════════

class SysMsg(ctk.CTkFrame):
    def __init__(self, parent, text, color=TEXT_LO, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=5)

        for _ in range(2):
            ctk.CTkFrame(row, fg_color=BD_DIM, height=1,
                         width=60, corner_radius=0).pack(side="left", padx=6)
            if _ == 0:
                ctk.CTkLabel(row, text=text, font=F(_MONO, 8),
                             text_color=color).pack(side="left")


# ══════════════════════════════════════════════════════════════════════════════
#  WIDGET: VOICE WAVEFORM CANVAS
# ══════════════════════════════════════════════════════════════════════════════

class WaveformCanvas(tk.Canvas):
    """
    Animated audio spectrum visualizer.
    Idle: slow dim cyan sine ripple
    Active: energetic cyan+purple neon bars
    """

    BAR_COUNT = 72

    def __init__(self, parent, **kw):
        kw.setdefault("bg", BG_SURFACE)
        kw.setdefault("highlightthickness", 0)
        kw.setdefault("height", 36)
        super().__init__(parent, **kw)
        self.active = False
        self._t = 0.0
        self._job = None
        self._tick()

    def _tick(self):
        self.delete("all")
        try:
            w = self.winfo_width() or 800
        except:
            w = 800
        h_mid = 18
        bars  = self.BAR_COUNT
        gap   = w / bars

        for i in range(bars):
            x   = i * gap + gap / 2
            t   = self._t
            pos = i / bars  # 0..1

            if self.active:
                # Energetic: multi-harmonic bars
                envelope = math.sin(pos * math.pi) ** 0.6
                h = envelope * (
                    abs(math.sin(t * 5.2 + i * 0.45)) * 13
                    + abs(math.sin(t * 8.7 + i * 0.72)) * 6
                    + abs(math.sin(t * 3.1 + i * 0.30)) * 4
                    + 1.5
                )
                # Color: fade cyan→purple by position
                r = int(pos * 168)
                g = int((1 - pos) * 212 + pos * 85)
                b = int((1 - pos) * 255 + pos * 247)
                brightness = min(1.0, h / 20)
                r = int(r * brightness)
                g = int(g * brightness)
                b = min(255, int(b * (0.6 + 0.4 * brightness)))
            else:
                # Idle: slow gentle ripple
                h = 1.8 + math.sin(t * 1.2 + i * 0.28) * 1.4
                r = 0
                g = int(30 + math.sin(t + i * 0.1) * 10)
                b = int(55 + math.sin(t * 0.8 + i * 0.15) * 20)

            color = f"#{max(0,min(255,r)):02x}{max(0,min(255,g)):02x}{max(0,min(255,b)):02x}"
            half  = max(1.2, gap * 0.38)
            self.create_rectangle(x - half, h_mid - h,
                                  x + half, h_mid + h,
                                  fill=color, outline="")

        self._t += 0.055
        self._job = self.after(42, self._tick)   # ~24 fps

    def destroy(self):
        if self._job:
            try: self.after_cancel(self._job)
            except: pass
        super().destroy()


# ══════════════════════════════════════════════════════════════════════════════
#  WIDGET: PULSE DOT (animated status indicator)
# ══════════════════════════════════════════════════════════════════════════════

class PulseDot(tk.Canvas):
    def __init__(self, parent, color=GREEN, size=10, **kw):
        kw.setdefault("bg", BG_SURFACE)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, width=size+8, height=size+8, **kw)
        self.color = color
        self._size = size
        self._phase = 0.0
        self._tick()

    def _tick(self):
        self.delete("all")
        cx = cy = (self._size + 8) / 2
        r  = self._size / 2
        # outer pulse ring
        pr = r + 3 + math.sin(self._phase) * 3
        alpha = int(80 + math.sin(self._phase) * 40)
        ring_col = self.color
        self.create_oval(cx-pr, cy-pr, cx+pr, cy+pr,
                        outline=ring_col, width=1)
        # inner solid dot
        self.create_oval(cx-r, cy-r, cx+r, cy+r,
                        fill=self.color, outline="")
        self._phase += 0.12
        self.after(50, self._tick)

    def set_color(self, c):
        self.color = c


# ══════════════════════════════════════════════════════════════════════════════
#  WIDGET: NAV BUTTON
# ══════════════════════════════════════════════════════════════════════════════

class NavBtn(ctk.CTkButton):
    def __init__(self, parent, icon, label, active=False, **kw):
        text = f"  {icon}   {label}"
        fg   = "#101c35" if active else "transparent"
        bc   = CYAN_DIM  if active else BG_SURFACE
        tc   = TEXT_HI   if active else TEXT_MED

        super().__init__(
            parent, text=text,
            font=F(_SANS, 12),
            height=40, anchor="w",
            fg_color=fg,
            hover_color="#0e1f38",
            border_width=1 if active else 0,
            border_color=bc,
            text_color=tc,
            corner_radius=10,
            **kw
        )
        if active:
            # Left neon bar effect via a label overlay (workaround)
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

class SaraUltra(ctk.CTk):

    def __init__(self):
        super().__init__()

        resolve_fonts()

        self.title("SARA AI  ·  Neural OS v3.0  ·  2026")
        self.geometry("1020x740")
        self.minsize(860, 600)
        self.configure(fg_color=BG_BASE)

        self.running      = False
        self._voice_stop  = threading.Event()
        self._typing_wid  = None   # TypingIndicator reference
        self._msg_count   = 0

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._build()
        self._start_clock()
        self._pulse_logo()

        # Welcome message after short delay
        self.after(600, self._post_welcome)
        self._speech_generation = 0
        self._active_speech_done = None

    # ══════════════════════════════════════════════════════════════════════════
    #  BUILD
    # ══════════════════════════════════════════════════════════════════════════

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()

    # ─── SIDEBAR ─────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        self._sb = ctk.CTkFrame(
            self, fg_color=BG_SURFACE, width=230,
            corner_radius=0,
            border_width=1, border_color=BD_SUBTLE
        )
        self._sb.grid(row=0, column=0, sticky="nsew")
        self._sb.grid_propagate(False)
        self._sb.grid_rowconfigure(4, weight=1)

        # ── Animated logo ──────────────────────────────────────────────────
        logo_frame = ctk.CTkFrame(self._sb, fg_color="transparent")
        logo_frame.grid(row=0, column=0, sticky="ew", padx=18, pady=(26, 14))

        # Hexagon-style badge on canvas
        self._logo_canvas = tk.Canvas(
            logo_frame, width=48, height=48,
            bg=BG_SURFACE, highlightthickness=0
        )
        self._logo_canvas.pack(side="left", padx=(0, 13))
        self._logo_phase = 0.0
        self._draw_logo()

        info = ctk.CTkFrame(logo_frame, fg_color="transparent")
        info.pack(side="left")
        ctk.CTkLabel(info, text="SARA",
                     font=F(_MONO, 18, "bold"),
                     text_color=CYAN).pack(anchor="w")
        ctk.CTkLabel(info, text="Neural OS  v3.0",
                     font=F(_MONO, 8),
                     text_color=TEXT_LO).pack(anchor="w")

        # ── Separator ─────────────────────────────────────────────────────
        ctk.CTkFrame(self._sb, fg_color=BD_SUBTLE, height=1,
                     corner_radius=0).grid(row=1, column=0, sticky="ew")

        # ── Status pill ───────────────────────────────────────────────────
        pill = ctk.CTkFrame(
            self._sb, fg_color=BG_GLASS, corner_radius=22,
            border_width=1, border_color=BD_DIM
        )
        pill.grid(row=2, column=0, sticky="ew", padx=16, pady=14)
        pill.grid_columnconfigure(1, weight=1)

        self._pulse = PulseDot(pill, color=GREEN, size=9, bg=BG_GLASS)
        self._pulse.grid(row=0, column=0, padx=(12, 0), pady=10)

        self._status_lbl = ctk.CTkLabel(
            pill, text="Online · Ready",
            font=F(_MONO, 9), text_color=TEXT_MED
        )
        self._status_lbl.grid(row=0, column=1, sticky="w", padx=8, pady=10)

        # ── Nav sections ──────────────────────────────────────────────────
        nav = ctk.CTkFrame(self._sb, fg_color="transparent")
        nav.grid(row=4, column=0, sticky="nsew", padx=12, pady=4)

        self._nav_section(nav, "WORKSPACE", [
            ("◈", "Chat",    True),
            ("⊘", "History", False),
            ("◎", "Alerts",  False),
        ])
        ctk.CTkFrame(nav, fg_color=BD_SUBTLE, height=1).pack(fill="x", pady=10)
        self._nav_section(nav, "TOOLS", [
            ("⬡", "Memory",    False),
            ("⚙", "Plugins",   False),
            ("◫", "Analytics", False),
            ("⌘", "Settings",  False),
        ])

        # ── Controls ──────────────────────────────────────────────────────
        ctrl = ctk.CTkFrame(self._sb, fg_color="transparent")
        ctrl.grid(row=5, column=0, sticky="ew", padx=14, pady=14)

        ctk.CTkFrame(ctrl, fg_color=BD_SUBTLE, height=1).pack(fill="x", pady=(0, 12))

        self._start_btn = ctk.CTkButton(
            ctrl,
            text="◉  Start Listening",
            font=F(_SANS, 12),
            height=42,
            fg_color=BG_GLASS,
            hover_color="#0a1e36",
            border_width=1,
            border_color=CYAN_DIM,
            text_color=TEXT_HI,
            corner_radius=12,
            command=self.start_voice
        )
        self._start_btn.pack(fill="x", pady=(0, 8))

        self._stop_btn = ctk.CTkButton(
            ctrl,
            text="■  Stop",
            font=F(_SANS, 12),
            height=40,
            fg_color="#1a0808",
            hover_color="#2d0d0d",
            border_width=1,
            border_color="#7f1d1d",
            text_color="#fca5a5",
            corner_radius=12,
            state="disabled",
            command=self.stop_voice
        )
        self._stop_btn.pack(fill="x")

        # Version tag
        ctk.CTkLabel(
            self._sb, text="© 2026  SARA Systems",
            font=F(_MONO, 7), text_color=TEXT_GHOST
        ).grid(row=6, column=0, pady=(4, 10))

    def _nav_section(self, parent, title, items):
        ctk.CTkLabel(parent, text=title,
                     font=F(_MONO, 7, "bold"),
                     text_color=TEXT_LO).pack(anchor="w", padx=8, pady=(8, 4))
        for icon, label, active in items:
            NavBtn(parent, icon, label, active).pack(fill="x", pady=2)

    # ─── LOGO ANIMATION ──────────────────────────────────────────────────────

    def _draw_logo(self):
        c   = self._logo_canvas
        c.delete("all")
        cx  = cy = 24
        r   = 18
        p   = self._logo_phase
        glow_r = r + 4 + math.sin(p) * 2

        # Outer glow ring
        gr_col = hex_blend(CYAN, PURPLE, (math.sin(p * 0.7) + 1) / 2)
        c.create_oval(cx - glow_r, cy - glow_r,
                      cx + glow_r, cy + glow_r,
                      outline=gr_col, width=1)

        # Hexagon
        pts = []
        for k in range(6):
            angle = math.radians(60 * k + p * 15)
            pts += [cx + r * math.cos(angle),
                    cy + r * math.sin(angle)]
        c.create_polygon(pts, outline=CYAN, fill=BG_SURFACE, width=1.5)

        # Inner S glyph
        c.create_text(cx, cy, text="S",
                      font=(_MONO, 14, "bold"),
                      fill=CYAN)

    def _pulse_logo(self):
        self._logo_phase += 0.06
        self._draw_logo()
        self.after(50, self._pulse_logo)

    # ─── MAIN PANEL ──────────────────────────────────────────────────────────

    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color=BG_BASE, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        self._build_topbar(main)
        self._build_chat(main)
        self._build_waveform(main)
        self._build_input(main)

    # ─── TOP BAR ─────────────────────────────────────────────────────────────

    def _build_topbar(self, parent):
        tb = ctk.CTkFrame(
            parent, fg_color=BG_SURFACE, height=56,
            corner_radius=0,
            border_width=1, border_color=BD_SUBTLE
        )
        tb.grid(row=0, column=0, sticky="ew")
        tb.grid_propagate(False)
        tb.grid_columnconfigure(1, weight=1)

        left = ctk.CTkFrame(tb, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=20, pady=14)

        ctk.CTkLabel(left, text="◈",
                     font=F(_MONO, 11), text_color=CYAN).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(left, text="Conversation  ·  Thread #001",
                     font=F(_MONO, 10), text_color=TEXT_MED).pack(side="left")

        # Right cluster
        right = ctk.CTkFrame(tb, fg_color="transparent")
        right.grid(row=0, column=2, sticky="e", padx=20)

        self._mode_badge = ctk.CTkLabel(
            right, text=" NEURAL ACTIVE ",
            font=F(_MONO, 8, "bold"),
            fg_color="#061a1a", text_color=CYAN,
            corner_radius=6, padx=8, pady=3
        )
        self._mode_badge.pack(side="left", padx=(0, 14))

        self._clock_lbl = ctk.CTkLabel(
            right, text="",
            font=F(_MONO, 9), text_color=TEXT_LO
        )
        self._clock_lbl.pack(side="left")

    # ─── CHAT AREA ───────────────────────────────────────────────────────────

    def _build_chat(self, parent):
        outer = ctk.CTkFrame(parent, fg_color=BG_BASE, corner_radius=0)
        self._chat_outer = outer
        outer.grid(row=1, column=0, sticky="nsew")
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        # Canvas + scrollbar
        self._chat_cv = tk.Canvas(
            outer, bg=BG_BASE, highlightthickness=0, bd=0
        )
        vsb = ctk.CTkScrollbar(
            outer, command=self._chat_cv.yview,
            fg_color=BG_BASE,
            button_color=BD_DIM,
            button_hover_color=CYAN_DIM
        )
        self._chat_cv.configure(yscrollcommand=vsb.set)
        self._chat_cv.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # Inner frame
        self._chat_inner = ctk.CTkFrame(self._chat_cv, fg_color=BG_BASE)
        self._chat_inner.grid_columnconfigure(0, weight=1)

        self._cv_win = self._chat_cv.create_window(
            (0, 0), window=self._chat_inner, anchor="nw"
        )
        self._chat_inner.bind("<Configure>", self._on_inner_cfg)
        self._chat_cv.bind("<Configure>",    self._on_cv_cfg)
        self._chat_scroll_active = False
        for widget in (outer, self._chat_cv, self._chat_inner):
            widget.bind("<Enter>", self._activate_chat_scroll)
            widget.bind("<Leave>", self._deactivate_chat_scroll)

    def _on_inner_cfg(self, e=None):
        self._chat_cv.configure(scrollregion=self._chat_cv.bbox("all"))

    def _on_cv_cfg(self, e):
        self._chat_cv.itemconfig(self._cv_win, width=e.width)

    def _activate_chat_scroll(self, event=None):
        if self._chat_scroll_active:
            return
        self._chat_scroll_active = True
        self.bind_all("<MouseWheel>", self._on_scroll)
        self.bind_all("<Button-4>", self._on_scroll_linux_up)
        self.bind_all("<Button-5>", self._on_scroll_linux_down)

    def _deactivate_chat_scroll(self, event=None):
        if not self._chat_scroll_active:
            return
        widget = self.winfo_containing(self.winfo_pointerx(), self.winfo_pointery())
        if self._widget_in_chat(widget):
            return
        self._chat_scroll_active = False
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")

    def _widget_in_chat(self, widget):
        while widget is not None:
            if widget == self._chat_outer:
                return True
            widget = widget.master
        return False

    def _on_scroll(self, e):
        if abs(e.delta) >= 120:
            self._chat_cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
        else:
            self._chat_cv.yview_scroll(int(-1 * e.delta), "units")

    def _on_scroll_linux_up(self, e):
        self._chat_cv.yview_scroll(-1, "units")

    def _on_scroll_linux_down(self, e):
        self._chat_cv.yview_scroll(1, "units")

    def _scroll_bottom(self):
        self._chat_inner.update_idletasks()
        self._chat_cv.yview_moveto(1.0)

    # ─── WAVEFORM BAR ────────────────────────────────────────────────────────

    def _build_waveform(self, parent):
        wf = ctk.CTkFrame(
            parent, fg_color=BG_SURFACE, height=64,
            corner_radius=0,
            border_width=1, border_color=BD_SUBTLE
        )
        wf.grid(row=2, column=0, sticky="ew")
        wf.grid_propagate(False)
        wf.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            wf, text="VOICE SPECTRUM",
            font=F(_MONO, 7, "bold"), text_color=TEXT_LO
        ).grid(row=0, column=0, sticky="nw", padx=20, pady=(8, 0))

        self._wave = WaveformCanvas(wf, bg=BG_SURFACE)
        self._wave.grid(row=1, column=0, columnspan=3, sticky="ew", padx=20, pady=(2, 8))
        wf.grid_columnconfigure(0, weight=1)

    # ─── INPUT BAR ───────────────────────────────────────────────────────────

    def _build_input(self, parent):
        inp_outer = ctk.CTkFrame(
            parent, fg_color=BG_SURFACE, corner_radius=0,
            border_width=1, border_color=BD_SUBTLE
        )
        inp_outer.grid(row=3, column=0, sticky="ew")
        inp_outer.grid_columnconfigure(0, weight=1)

        # Floating glassmorphism input card
        card = ctk.CTkFrame(
            inp_outer,
            fg_color=BG_GLASS,
            corner_radius=18,
            border_width=1,
            border_color=BD_MED
        )
        card.grid(row=0, column=0, sticky="ew", padx=18, pady=12)
        card.grid_columnconfigure(0, weight=1)

        self._inp = ctk.CTkEntry(
            card,
            placeholder_text="  Send a message to SARA…",
            font=F(_SANS, 13),
            fg_color="transparent",
            border_width=0,
            text_color=TEXT_HI,
            placeholder_text_color=TEXT_LO,
            height=46
        )
        self._inp.grid(row=0, column=0, sticky="ew", padx=(12, 4), pady=6)
        self._inp.bind("<Return>", self.send_text)
        self._inp.bind("<FocusIn>",  self._inp_focus_in)
        self._inp.bind("<FocusOut>", self._inp_focus_out)

        send = ctk.CTkButton(
            card,
            text="↑",
            width=42, height=42,
            font=F(_MONO, 18, "bold"),
            fg_color=CYAN,
            hover_color=CYAN_DIM,
            text_color=BG_VOID,
            corner_radius=13,
            command=self.send_text
        )
        send.grid(row=0, column=1, padx=(0, 6), pady=6)

        ctk.CTkLabel(
            inp_outer,
            text='⏎ Enter to send   ·   "Hey SARA" for voice mode   ·   "sleep" to pause',
            font=F(_MONO, 8), text_color=TEXT_LO
        ).grid(row=1, column=0, pady=(0, 8))

    def _inp_focus_in(self, e=None):
        pass   # could animate border glow

    def _inp_focus_out(self, e=None):
        pass

    # ══════════════════════════════════════════════════════════════════════════
    #  CHAT HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _add_bubble(self, sender, text, is_ai=True):
        bub = ChatBubble(self._chat_inner, sender, text, is_ai=is_ai)
        bub.pack(fill="x", padx=4, pady=1)
        self._msg_count += 1
        self._scroll_bottom()

    def _add_sys(self, text, color=TEXT_LO):
        SysMsg(self._chat_inner, text, color=color).pack(fill="x", padx=8)
        self._scroll_bottom()

    def _show_typing(self):
        self._hide_typing()
        self._typing_wid = TypingIndicator(self._chat_inner)
        self._typing_wid.pack(fill="x", padx=4, pady=2)
        self._scroll_bottom()

    def _hide_typing(self):
        if self._typing_wid:
            try:
                self._typing_wid.destroy()
            except:
                pass
            self._typing_wid = None

    # ══════════════════════════════════════════════════════════════════════════
    #  STATUS
    # ══════════════════════════════════════════════════════════════════════════

    def _set_status(self, text, color=GREEN):
        def _do():
            self._status_lbl.configure(text=text)
            self._pulse.set_color(color)
        self.after(0, _do)

    def _speak_ai_response(self, text, ready_status="🟢 Online · Ready", ready_color=GREEN):
        if not str(text or "").strip():
            done_event = threading.Event()
            done_event.set()
            self._set_status(ready_status, ready_color)
            return done_event

        if self._active_speech_done:
            self._active_speech_done.set()

        self._speech_generation += 1
        generation = self._speech_generation
        done_event = threading.Event()
        self._active_speech_done = done_event

        def on_start():
            self.after(0, lambda: self._set_status("🔊 Speaking...", CYAN))

        def on_done():
            if generation == self._speech_generation:
                self._active_speech_done = None
                self.after(0, lambda: self._set_status(ready_status, ready_color))
            done_event.set()

        def on_error(exc):
            print(f"[TTS error] {exc}")
            on_done()

        speak_response(text, on_start=on_start, on_done=on_done, on_error=on_error)
        return done_event

    # ══════════════════════════════════════════════════════════════════════════
    #  CLOCK
    # ══════════════════════════════════════════════════════════════════════════

    def _start_clock(self):
        self._clock_lbl.configure(
            text=time.strftime("%a %d %b  %H:%M:%S")
        )
        self.after(1000, self._start_clock)

    # ══════════════════════════════════════════════════════════════════════════
    #  WELCOME
    # ══════════════════════════════════════════════════════════════════════════

    def _post_welcome(self):
        self._add_sys(f"── Session initialized · {time.strftime('%H:%M')} ──", CYAN_DIM)
        self._add_bubble(
            "SARA",
            "System online. Neural pathways synchronized.\n\n"
            "I'm SARA — your Smart Adaptive Response Agent.\n"
            "Ready for analysis, code generation, research,\n"
            "or any cognitive task you require.",
            is_ai=True
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  SEND / REPLY
    # ══════════════════════════════════════════════════════════════════════════

    def send_text(self, event=None):
        msg = self._inp.get().strip()
        if not msg:
            return
        self._inp.delete(0, "end")
        self.after(0, lambda: self._add_bubble("You", msg, is_ai=False))
        threading.Thread(target=self._reply_thread,
                         args=(msg,), daemon=True).start()

    def _reply_thread(self, msg):
        self._set_status("Processing…", CYAN)
        self.after(0, self._show_typing)
        self._wave.active = True

        response = ask_ai(msg)

        def show_and_speak():
            self._hide_typing()
            self._add_bubble("SARA", response, is_ai=True)
            self._speak_ai_response(response)
            self._wave.active = False

        self.after(0, show_and_speak)

    # ══════════════════════════════════════════════════════════════════════════
    #  VOICE MODE
    # ══════════════════════════════════════════════════════════════════════════

    def start_voice(self):
        if self.running:
            return
        self.running = True
        self._voice_stop.clear()
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._wave.active = True
        self._set_status("Listening…", CYAN)
        threading.Thread(target=self._voice_loop, daemon=True).start()

    def stop_voice(self):
        self.running = False
        self._voice_stop.set()
        stop_speech()
        if self._active_speech_done:
            self._active_speech_done.set()
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._wave.active = False
        self._set_status("Online · Ready", GREEN)
        self.after(0, lambda: self._add_sys("Voice session terminated."))

    def _voice_loop(self):
        while self.running and not self._voice_stop.is_set():
            self._set_status("Awaiting wake word…", AMBER)
            self.after(0, lambda: self._add_sys("⬡  Say 'Hey SARA' to begin…"))
            if not wait_for_wake_word(stop_event=self._voice_stop):
                break
            if not self.running or self._voice_stop.is_set():
                break

            speak_smart("I'm listening.")
            self.after(0, lambda: self._add_sys("◈  Wake word detected — online.", CYAN))
            self._set_status("Active · Listening", GREEN)

            while self.running and not self._voice_stop.is_set():
                self._set_status("Capturing audio…", CYAN)
                command = listen(
                    timeout=8,
                    phrase_time_limit=12,
                    stop_event=self._voice_stop,
                )
                if self._voice_stop.is_set() or not self.running:
                    break
                if not command:
                    continue

                cmd = command
                self.after(0, lambda c=cmd: self._add_bubble("You", c, is_ai=False))

                if any(w in command.lower() for w in
                       ["exit", "stop", "goodbye", "bye"]):
                    display_done = threading.Event()

                    def show_exit():
                        self._add_bubble(
                            "SARA", "Session terminated. Goodbye. 👋", is_ai=True)
                        display_done.set()

                    self.after(0, show_exit)
                    display_done.wait()
                    self._speak_ai_response("Session terminated. Goodbye.").wait()
                    self.after(0, self.stop_voice)
                    return

                if "sleep" in command.lower():
                    display_done = threading.Event()

                    def show_sleep():
                        self._add_bubble(
                            "SARA", "◎ Standby mode — Say 'Hey SARA' to resume.",
                            is_ai=True)
                        display_done.set()

                    self.after(0, show_sleep)
                    display_done.wait()
                    self._speak_ai_response(
                        "Entering standby. Say Hey SARA to resume.").wait()
                    break

                self._set_status("Neural processing…", PURPLE)
                self.after(0, self._show_typing)
                self._wave.active = True

                response = ask_ai(command)

                display_done = threading.Event()

                def show_and_speak_voice(r=response):
                    self._hide_typing()
                    self._add_bubble("SARA", r, is_ai=True)
                    self._wave.active = True
                    display_done.set()

                self.after(0, show_and_speak_voice)
                display_done.wait()
                self._speak_ai_response(response).wait()


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = SaraUltra()
    app.mainloop()
