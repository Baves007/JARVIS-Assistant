"""
JARVIS Dashboard — Iron Man HUD  (fully responsive)
Every element scales proportionally when the window is resized.
"""

import pygame
import math
import time
import random
import datetime
import sys

# ─── Colour Palette — Black & Orange Theme ────────────────────────────────────
C_BG    = (  6,   4,   2)   # near-pure black with warm tint
C_RING1 = (255, 120,   0)   # vivid orange  — primary ring
C_RING2 = (255, 200,  50)   # amber gold    — secondary / headers
C_RING3 = (200,  60,   0)   # deep burnt orange — inner ring accent
C_ALERT = (255,  40,  40)   # red alert
C_GREEN = (255, 165,   0)   # re-mapped: bright orange for "online" status
C_TEXT  = (255, 220, 170)   # warm cream white — body text
C_DIM   = ( 90,  55,  20)   # dark amber — panel borders / dim elements
C_PANEL = ( 14,   8,   2)   # very dark warm black — panel background
C_WHITE = (255, 240, 210)   # warm white for core centre dot

# ─── Base design resolution (scale = 1.0) ──────────────────────────────────────
BASE_W      = 1280
BASE_H      =  780
BASE_RADIUS =  200


# ══════════════════════════════════════════════════════════════════════════════
class Particle:
    def __init__(self):
        self._cx = BASE_W // 2
        self._cy = BASE_H // 2 + 30
        self._r  = BASE_RADIUS
        self.reset()

    def update_anchor(self, cx, cy, radius):
        self._cx = cx
        self._cy = cy
        self._r  = radius

    def reset(self):
        angle     = random.uniform(0, math.tau)
        r_spawn   = random.uniform(self._r + 20, self._r + self._r * 0.8)
        self.x    = self._cx + math.cos(angle) * r_spawn
        self.y    = self._cy + math.sin(angle) * r_spawn
        self.vx   = random.uniform(-0.4, 0.4)
        self.vy   = random.uniform(-0.4, 0.4)
        self.life = random.uniform(0.3, 1.0)
        self.maxl = self.life
        self.rad  = random.randint(1, 3)
        self.col  = random.choice([C_RING1, C_RING2, C_RING3])

    def update(self):
        self.x   += self.vx
        self.y   += self.vy
        self.life -= 0.004
        if self.life <= 0:
            self.reset()

    def draw(self, surf):
        alpha = max(0, int(255 * (self.life / self.maxl)))
        s = pygame.Surface((self.rad*2, self.rad*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.col, alpha), (self.rad, self.rad), self.rad)
        surf.blit(s, (int(self.x - self.rad), int(self.y - self.rad)))


# ══════════════════════════════════════════════════════════════════════════════
class JarvisDashboard:

    def __init__(self, jarvis_core):
        self.jarvis = jarvis_core
        pygame.init()
        pygame.display.set_caption("JARVIS — AI Assistant")
        self.screen = pygame.display.set_mode((BASE_W, BASE_H), pygame.RESIZABLE)
        self.clock  = pygame.time.Clock()
        self.W      = BASE_W
        self.H      = BASE_H

        # Animation state
        self.angle1     =   0.0
        self.angle2     = 120.0
        self.angle3     = 240.0
        self.pulse      =   0.0
        self.scan_y     =   0
        self.wake_flash =   0.0
        self.eq_bars    = [0.0] * 32
        self.particles  = [Particle() for _ in range(80)]
        self.chat_lines = []

        self._rebuild_scale()

    # ── Scale helpers ──────────────────────────────────────────────────────────

    def _rebuild_scale(self):
        self.scale  = min(self.W / BASE_W, self.H / BASE_H)
        self.cx     = self.W // 2
        self.cy     = int(self.H // 2 + 30 * self.scale)
        self.radius = int(BASE_RADIUS * self.scale)
        self._load_fonts()

    def _s(self, v):
        return max(1, int(v * self.scale))

    def _load_fonts(self):
        mono  = next((n for n in ["Consolas","Courier New","DejaVu Sans Mono"]
                      if self._fe(n)), "monospace")
        clean = next((n for n in ["Arial","Tahoma","Verdana","Segoe UI"]
                      if self._fe(n)), mono)
        sc = self.scale
        self.font_tiny   = pygame.font.SysFont(mono,  max(10, int(14*sc)), bold=True)
        self.font_small  = pygame.font.SysFont(clean, max(12, int(17*sc)), bold=True)
        self.font_medium = pygame.font.SysFont(clean, max(14, int(22*sc)), bold=True)
        self.font_large  = pygame.font.SysFont(clean, max(18, int(30*sc)), bold=True)
        self.font_title  = pygame.font.SysFont(clean, max(24, int(44*sc)), bold=True)

    @staticmethod
    def _fe(name):
        try:
            pygame.font.SysFont(name, 12)
            return True
        except Exception:
            return False

    # ── Main loop ──────────────────────────────────────────────────────────────

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.W, self.H = event.w, event.h
                    self.screen = pygame.display.set_mode(
                        (self.W, self.H), pygame.RESIZABLE)
                    self._rebuild_scale()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_RETURN:
                        self.jarvis.post_event("wake", "")
                    elif event.key == pygame.K_SPACE:
                        self.jarvis.process_command("what is the time")

            while not self.jarvis.event_queue.empty():
                ev = self.jarvis.event_queue.get_nowait()
                if ev["type"] == "speak":
                    self.chat_lines.append((time.time(), f"JARVIS ▶ {ev['data']}"))
                    if len(self.chat_lines) > 8:
                        self.chat_lines.pop(0)
                elif ev["type"] == "command":
                    self.chat_lines.append((time.time(), f"You    ▶ {ev['data']}"))
                    if len(self.chat_lines) > 8:
                        self.chat_lines.pop(0)
                elif ev["type"] == "wake":
                    self.wake_flash = 1.0

            if self.wake_flash > 0:
                self.wake_flash = max(0.0, self.wake_flash - dt * 1.5)

            amp   = self.jarvis.mic_amplitude
            awake = self.jarvis.is_awake
            sp    = 3.0 if awake else 1.0

            self.angle1 = (self.angle1 + dt * 35 * sp) % 360
            self.angle2 = (self.angle2 - dt * 22 * sp) % 360
            self.angle3 = (self.angle3 + dt * 15 * sp) % 360
            self.pulse  = (self.pulse  + dt * 2.5)      % math.tau
            self.scan_y = (self.scan_y + int(dt * 120)) % self.H

            for i in range(len(self.eq_bars)):
                tgt = amp * (0.3 + 0.7 * abs(math.sin(time.time()*(2+i*0.3)+i)))
                self.eq_bars[i] += (tgt - self.eq_bars[i]) * 0.25

            for p in self.particles:
                p.update_anchor(self.cx, self.cy, self.radius)
                p.update()

            self.screen.fill(C_BG)
            self._draw_grid()
            self._draw_scan_line()
            self._draw_particles()
            self._draw_glow(awake)
            self._draw_outer_decorations()
            self._draw_rings()
            self._draw_center_core(awake, amp)
            self._draw_equaliser(amp)
            self._draw_info_panels()
            self._draw_chat_log()
            self._draw_status_bar()
            self._draw_top_header()
            self._draw_wake_flash()

            pygame.display.flip()

        pygame.quit()
        sys.exit(0)

    # ── Draw routines ──────────────────────────────────────────────────────────

    def _draw_grid(self):
        surf = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        step = self._s(40)
        for x in range(0, self.W, step):
            pygame.draw.line(surf, (255, 100, 0, 10), (x, 0), (x, self.H))
        for y in range(0, self.H, step):
            pygame.draw.line(surf, (255, 100, 0, 10), (0, y), (self.W, y))
        self.screen.blit(surf, (0, 0))

    def _draw_scan_line(self):
        surf = pygame.Surface((self.W, 3), pygame.SRCALPHA)
        surf.fill((255, 140, 0, 18))
        self.screen.blit(surf, (0, self.scan_y))

    def _draw_particles(self):
        for p in self.particles:
            p.draw(self.screen)

    def _draw_glow(self, awake):
        r    = self.radius
        gs   = r * 4
        surf = pygame.Surface((gs, gs), pygame.SRCALPHA)
        col  = C_RING2 if awake else C_RING1
        for rad in range(r, 0, -4):
            alpha = int(30 * (1 - rad / r))
            pygame.draw.circle(surf, (*col, alpha), (gs//2, gs//2), rad)
        self.screen.blit(surf, (self.cx - gs//2, self.cy - gs//2))

    def _draw_arc(self, cx, cy, r, s_deg, e_deg, color, w=2):
        rect = pygame.Rect(cx-r, cy-r, r*2, r*2)
        pygame.draw.arc(self.screen, color, rect,
                        math.radians(s_deg), math.radians(e_deg),
                        max(1, int(w * self.scale)))

    def _draw_rings(self):
        cx, cy, R = self.cx, self.cy, self.radius
        for i in range(6):
            s = self.angle1 + i*60
            self._draw_arc(cx, cy, R+self._s(60), s, s+40, C_RING1, 2)
        for i in range(4):
            s = self.angle2 + i*90
            self._draw_arc(cx, cy, R+self._s(30), s, s+65, C_RING2, 3)
        for i in range(8):
            s = self.angle3 + i*45
            self._draw_arc(cx, cy, R+self._s(8),  s, s+28, C_RING3, 2)
        pygame.draw.circle(self.screen, C_DIM, (cx, cy), R,             1)
        pygame.draw.circle(self.screen, C_DIM, (cx, cy), R+self._s(5),  1)
        for i in range(36):
            angle = math.radians(i * 10)
            r_in  = R + self._s(62)
            r_out = r_in + self._s(8 if i%9==0 else 4 if i%3==0 else 2)
            x1 = cx + math.cos(angle)*r_in;  y1 = cy + math.sin(angle)*r_in
            x2 = cx + math.cos(angle)*r_out; y2 = cy + math.sin(angle)*r_out
            pygame.draw.line(self.screen, C_RING1 if i%9==0 else C_DIM,
                             (int(x1),int(y1)), (int(x2),int(y2)), 1)

    def _draw_center_core(self, awake, amp):
        cx, cy  = self.cx, self.cy
        pr      = self._s(12) + self._s(8) * math.sin(self.pulse)
        col     = C_RING2 if awake else C_RING1
        gr      = self._s(20)
        for ro in range(gr, 0, -2):
            alpha = int(180*(1-ro/gr)*(0.4+0.6*amp))
            s = pygame.Surface((ro*2, ro*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, alpha), (ro, ro), ro)
            self.screen.blit(s, (cx-ro, cy-ro))
        pygame.draw.circle(self.screen, col,    (cx,cy), int(pr), 0)
        pygame.draw.circle(self.screen, C_WHITE,(cx,cy), max(1,int(pr)-self._s(4)), 0)
        for i in range(6):
            a  = math.radians(i*60 + self.angle3)
            x1 = cx+math.cos(a)*self._s(6);  y1 = cy+math.sin(a)*self._s(6)
            x2 = cx+math.cos(a)*self._s(18); y2 = cy+math.sin(a)*self._s(18)
            pygame.draw.line(self.screen, col, (int(x1),int(y1)), (int(x2),int(y2)), 1)

    def _draw_equaliser(self, amp):
        cx, cy  = self.cx, self.cy
        n       = 32
        r_inner = self.radius + self._s(72)
        for i, h in enumerate(self.eq_bars):
            angle = math.radians(200 + i*(140/n))
            r_out = r_inner + max(2, int(h * self._s(55)))
            x1 = cx+math.cos(angle)*r_inner; y1 = cy+math.sin(angle)*r_inner
            x2 = cx+math.cos(angle)*r_out;   y2 = cy+math.sin(angle)*r_out
            ratio = i/n
            # Equaliser gradient: burnt orange → vivid orange → amber
            rc = int(180*(1-ratio) + 255*ratio)
            gc = int( 40*(1-ratio) + 200*ratio)
            bc = int(  0*(1-ratio) +  50*ratio)
            pygame.draw.line(self.screen, (rc,gc,bc),
                             (int(x1),int(y1)), (int(x2),int(y2)), 2)

    def _draw_outer_decorations(self):
        bk = self._s(30); mg = self._s(20); col = C_RING1
        W, H = self.W, self.H
        pygame.draw.lines(self.screen, col, False,
            [(mg, mg+bk),(mg,mg),(mg+bk,mg)], 2)
        pygame.draw.lines(self.screen, col, False,
            [(W-mg-bk,mg),(W-mg,mg),(W-mg,mg+bk)], 2)
        pygame.draw.lines(self.screen, col, False,
            [(mg,H-mg-bk),(mg,H-mg),(mg+bk,H-mg)], 2)
        pygame.draw.lines(self.screen, col, False,
            [(W-mg-bk,H-mg),(W-mg,H-mg),(W-mg,H-mg-bk)], 2)
        pygame.draw.line(self.screen, C_DIM, (mg, self._s(80)), (W-mg, self._s(80)), 1)
        pygame.draw.line(self.screen, C_DIM, (mg, H-self._s(60)), (W-mg, H-self._s(60)), 1)

    def _draw_info_panels(self):
        mg  = self._s(30)
        pw  = self._s(250)
        top = self._s(100)
        lh  = self._s(19)
        now = datetime.datetime.now()

        # LEFT — box height auto-fits all content
        lx = mg
        left_lines = [
            ("SYSTEM STATUS",     C_RING2, self.font_small),
            ("",                  C_TEXT,  self.font_tiny),
            (f"TIME   {now.strftime('%H:%M:%S')}", C_TEXT, self.font_tiny),
            (f"DATE   {now.strftime('%d %b %Y')}",  C_TEXT, self.font_tiny),
            ("",                  C_TEXT,  self.font_tiny),
            ("CORE    ONLINE",    C_GREEN, self.font_tiny),
            ("SPEECH  READY",     C_GREEN, self.font_tiny),
            ("TTS     ACTIVE",    C_GREEN, self.font_tiny),
            ("AI      ARMED",     C_GREEN, self.font_tiny),
            ("",                  C_TEXT,  self.font_tiny),
            ("COMMANDS",          C_RING2, self.font_small),
            ("",                  C_TEXT,  self.font_tiny),
            ("• open youtube",    C_TEXT,  self.font_tiny),
            ("• open google",     C_TEXT,  self.font_tiny),
            ("• play music",      C_TEXT,  self.font_tiny),
            ("• take screenshot", C_TEXT,  self.font_tiny),
            ("• what's the time", C_TEXT,  self.font_tiny),
            ("• weather in NYC",  C_TEXT,  self.font_tiny),
            ("• search wikipedia",C_TEXT,  self.font_tiny),
            ("• shutdown system", C_TEXT,  self.font_tiny),
            ("• tell me a joke",  C_TEXT,  self.font_tiny),
        ]
        left_h = self._s(10) + len(left_lines) * lh + self._s(14)
        self._draw_panel(lx, top, pw, left_h)
        self._render_lines(left_lines, lx+self._s(12), top+self._s(10), lh)

        # RIGHT
        rx = self.W - mg - pw
        self._draw_panel(rx, top, pw, self._s(320))
        mic_fill  = '▓' * int(self.jarvis.mic_amplitude * 14)
        mic_empty = '░' * (14 - int(self.jarvis.mic_amplitude * 14))
        self._render_lines([
            ("SENSOR ARRAY",           C_RING2, self.font_small),
            ("",                       C_TEXT,  self.font_tiny),
            (f"MIC  {mic_fill}{mic_empty}", C_RING2, self.font_tiny),
            ("",                       C_TEXT,  self.font_tiny),
            ("WAKE WORD",              C_RING2, self.font_small),
            ("  'Hey Jarvis'",         C_TEXT,  self.font_tiny),
            ("",                       C_TEXT,  self.font_tiny),
            ("AI ENGINE",              C_RING2, self.font_small),
            ("  Groq Cloud  \u2713",   C_GREEN, self.font_tiny),
            ("  llama3-8b-8192",       C_TEXT,  self.font_tiny),
            ("  Ultra-fast responses", C_TEXT,  self.font_tiny),
            ("",                       C_TEXT,  self.font_tiny),
            ("KEYBOARD",               C_RING2, self.font_small),
            ("  ENTER = wake",         C_TEXT,  self.font_tiny),
            ("  SPACE = time",         C_TEXT,  self.font_tiny),
            ("  ESC   = quit",         C_TEXT,  self.font_tiny),
        ], rx+self._s(12), top+self._s(10), lh)

    def _draw_chat_log(self):
        bw = self._s(640)
        bh = self._s(145)
        bx = self.cx - bw//2
        by = self.cy + self.radius + self._s(90)
        if by + bh > self.H - self._s(65):
            by = self.H - self._s(65) - bh
        self._draw_panel(bx, by, bw, bh)
        self.screen.blit(
            self.font_small.render("COMM LOG", True, C_RING2),
            (bx+self._s(10), by+self._s(8)))
        pygame.draw.line(self.screen, C_DIM,
                         (bx+self._s(10), by+self._s(28)),
                         (bx+bw-self._s(10), by+self._s(28)), 1)
        y_off = by+self._s(36)
        for ts, line in self.chat_lines[-5:]:
            col   = C_RING2 if "JARVIS" in line else C_GREEN
            trunc = line[:78]+"…" if len(line)>78 else line
            self.screen.blit(
                self.font_small.render(trunc, True, col),
                (bx+self._s(12), y_off))
            y_off += self._s(20)
            if y_off > by+bh-self._s(10):
                break

    def _draw_status_bar(self):
        msg   = self.jarvis.status_message
        trunc = msg[:95]+"…" if len(msg)>95 else msg
        surf  = self.font_medium.render(trunc, True, C_TEXT)
        self.screen.blit(surf, (self.cx-surf.get_width()//2, self.H-self._s(52)))
        col   = C_GREEN if self.jarvis.is_awake else C_RING1
        dx, dy = self.W-self._s(40), self.H-self._s(42)
        pygame.draw.circle(self.screen, col, (dx, dy), self._s(7))
        lbl = self.font_tiny.render(
            "ACTIVE" if self.jarvis.is_awake else "STANDBY", True, col)
        self.screen.blit(lbl, (dx-self._s(55), dy-self._s(7)))

    def _draw_top_header(self):
        title = self.font_title.render("J . A . R . V . I . S", True, C_RING1)
        sub   = self.font_small.render(
            "Just A Rather Very Intelligent System  —  AI Assistant v4.2", True, C_DIM)
        self.screen.blit(title, (self.cx-title.get_width()//2, self._s(16)))
        self.screen.blit(sub,   (self.cx-sub.get_width()//2,   self._s(58)))

    def _draw_wake_flash(self):
        if self.wake_flash > 0.01:
            surf = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            surf.fill((255, 140, 0, int(50*self.wake_flash)))
            self.screen.blit(surf, (0, 0))

    # ── Utility ────────────────────────────────────────────────────────────────

    def _draw_panel(self, x, y, w, h):
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((*C_PANEL, 200))
        self.screen.blit(surf, (x, y))
        pygame.draw.rect(self.screen, C_DIM, (x, y, w, h), 1)
        ca = self._s(6)
        for dx, dy in [(0,0),(w-ca,0),(0,h-ca),(w-ca,h-ca)]:
            pygame.draw.rect(self.screen, C_RING1, (x+dx, y+dy, ca, ca), 1)

    def _render_lines(self, lines, x, y, line_h):
        cy = y
        for text, color, font in lines:
            if text:
                self.screen.blit(font.render(text, True, color), (x, cy))
            cy += line_h
