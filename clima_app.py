"""
Clima EM - App de escritorio con ilustración dinámica
Requiere: pip install PyQt6 requests
Usa tu Flask backend o llama directamente a OpenWeather API
"""

import sys
import os
import math
import random
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QRect, QPointF, QRectF
)
from PyQt6.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient,
    QFont, QPen, QBrush, QPainterPath, QPolygonF
)

# ─────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────
# Opción A: usar tu Flask backend
FLASK_BASE = os.environ.get("FLASK_URL", "http://localhost:5000")
USE_FLASK   = True   # Cambia a True si tu Flask está corriendo

# Opción B: llamar directo a OpenWeather (sin Flask)
OW_API_KEY = "993f79c3eb30586d10c7acedaf14a76e"   # ← pon tu key aquí
OW_BASE    = "https://api.openweathermap.org/data/2.5/weather"

# ─────────────────────────────────────────────
#  HILO DE RED (no bloquea la UI)
# ─────────────────────────────────────────────
class WeatherWorker(QThread):
    result  = pyqtSignal(dict)
    error   = pyqtSignal(str)

    def __init__(self, city: str):
        super().__init__()
        self.city = city

    def run(self):
        try:
            if USE_FLASK:
                r = requests.get(f"{FLASK_BASE}/weather", params={"city": self.city}, timeout=6)
                data = r.json()
                if not data.get("success"):
                    self.error.emit(data.get("message", "Ciudad no encontrada"))
                    return
                d = data["data"]
                payload = {
                    "city":        d["city"],
                    "country":     d["country"],
                    "temp":        d["temperature"]["current"],
                    "feels_like":  d["temperature"]["feels_like"],
                    "condition":   d["weather"]["main"],        # "Rain", "Clear", etc.
                    "description": d["weather"]["description"],
                    "humidity":    d["atmospheric"]["humidity"],
                    "wind":        d["wind"]["speed"],
                    "pressure":    d["atmospheric"]["pressure"],
                }
            else:
                r = requests.get(OW_BASE, params={
                    "q": self.city, "appid": OW_API_KEY,
                    "units": "metric", "lang": "es"
                }, timeout=6)
                if r.status_code == 404:
                    self.error.emit("Ciudad no encontrada")
                    return
                if r.status_code == 401:
                    self.error.emit("API key inválida")
                    return
                d = r.json()
                payload = {
                    "city":        d["name"],
                    "country":     d["sys"]["country"],
                    "temp":        d["main"]["temp"],
                    "feels_like":  d["main"]["feels_like"],
                    "condition":   d["weather"][0]["main"],
                    "description": d["weather"][0]["description"],
                    "humidity":    d["main"]["humidity"],
                    "wind":        d["wind"]["speed"],
                    "pressure":    d["main"]["pressure"],
                }
            self.result.emit(payload)
        except requests.exceptions.ConnectionError:
            self.error.emit("Sin conexión. ¿Está corriendo el servidor?" if USE_FLASK
                            else "Sin conexión a internet")
        except Exception as e:
            self.error.emit(str(e))


# ─────────────────────────────────────────────
#  MAPA DE CONDICIÓN → ESCENA
# ─────────────────────────────────────────────
def condition_to_scene(condition: str) -> str:
    c = condition.lower()
    if "thunderstorm" in c:          return "thunderstorm"
    if "drizzle" in c:               return "drizzle"
    if "rain" in c:                  return "rain"
    if "snow" in c:                  return "snow"
    if "mist" in c or "fog" in c:   return "fog"
    if "haze" in c or "smoke" in c: return "haze"
    if "clear" in c:                 return "clear"
    if "cloud" in c:                 return "cloudy"
    if "sand" in c or "dust" in c:  return "haze"
    return "cloudy"

SCENE_PALETTES = {
    "clear":       {"sky_top": "#1a6dbd", "sky_bot": "#f7c948", "ground": "#3d8c40"},
    "cloudy":      {"sky_top": "#607d8b", "sky_bot": "#b0bec5", "ground": "#5a7a5a"},
    "rain":        {"sky_top": "#263238", "sky_bot": "#546e7a", "ground": "#37474f"},
    "drizzle":     {"sky_top": "#37474f", "sky_bot": "#78909c", "ground": "#455a64"},
    "thunderstorm":{"sky_top": "#1a1a2e", "sky_bot": "#3a3a5c", "ground": "#2d3436"},
    "snow":        {"sky_top": "#b0bec5", "sky_bot": "#eceff1", "ground": "#e0e0e0"},
    "fog":         {"sky_top": "#9e9e9e", "sky_bot": "#eeeeee", "ground": "#bdbdbd"},
    "haze":        {"sky_top": "#8d6e63", "sky_bot": "#d7a97a", "ground": "#795548"},
}


# ─────────────────────────────────────────────
#  WIDGET DE ILUSTRACIÓN
# ─────────────────────────────────────────────
class WeatherScene(QWidget):
    def __init__(self):
        super().__init__()
        self.scene    = "clear"
        self.tick     = 0
        self.drops    = []   # lluvia
        self.flakes   = []   # nieve
        self.clouds   = []   # nubes animadas
        self.lightning= False
        self.lightning_timer = 0
        self.setMinimumHeight(280)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(40)  # ~25 fps

    def set_scene(self, scene: str):
        self.scene = scene
        self.drops  = [(random.uniform(0,1), random.uniform(0,1), random.uniform(0.015,0.03))
                       for _ in range(120)]
        self.flakes = [(random.uniform(0,1), random.uniform(0,1),
                        random.uniform(4,10), random.uniform(0.003,0.008))
                       for _ in range(80)]
        self.clouds = [(random.uniform(-0.2, 1.2), random.uniform(0.05, 0.35),
                        random.uniform(0.5, 1.2), random.uniform(0.0008, 0.002))
                       for _ in range(5)]
        self.update()

    def _animate(self):
        self.tick += 1
        w, h = self.width(), self.height()

        # Lluvia
        self.drops = [
            (x, (y + spd) % 1.0, spd)
            for (x, y, spd) in self.drops
        ]
        # Nieve
        self.flakes = [
            ((x + math.sin(y * 10 + self.tick * 0.05) * 0.003) % 1.0,
             (y + spd) % 1.0, r, spd)
            for (x, y, r, spd) in self.flakes
        ]
        # Nubes (solo mover cada 15 ticks)
        if self.tick % 15 == 0:
            self.clouds = [
                ((cx + spd) % 1.4 - 0.2, cy, scale, spd)
                for (cx, cy, scale, spd) in self.clouds
            ]
        # Relámpago
        if self.scene == "thunderstorm" and self.tick % 80 == 0:
            self.lightning = True
            self.lightning_timer = 6
        if self.lightning_timer > 0:
            self.lightning_timer -= 1
        else:
            self.lightning = False

        self.update()

    # ── PINTADO ──────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = SCENE_PALETTES.get(self.scene, SCENE_PALETTES["cloudy"])
        w, h = self.width(), self.height()
        horizon = int(h * 0.68)

        self._draw_sky(p, w, h, horizon, pal)
        self._draw_scene_elements(p, w, h, horizon)
        self._draw_ground(p, w, h, horizon, pal)
        p.end()

    def _draw_sky(self, p, w, h, horizon, pal):
        grad = QLinearGradient(0, 0, 0, horizon)
        grad.setColorAt(0, QColor(pal["sky_top"]))
        grad.setColorAt(1, QColor(pal["sky_bot"]))
        p.fillRect(0, 0, w, horizon, grad)

        # Flash de relámpago
        if self.lightning:
            p.fillRect(0, 0, w, horizon, QColor(255, 255, 200, 80))

    def _draw_ground(self, p, w, h, horizon, pal):
        grad = QLinearGradient(0, horizon, 0, h)
        col = QColor(pal["ground"])
        grad.setColorAt(0, col.lighter(130))
        grad.setColorAt(1, col.darker(130))
        p.fillRect(0, horizon, w, h - horizon, grad)

        # Línea de pasto/suelo
        pen = QPen(QColor(pal["ground"]).darker(160), 2)
        p.setPen(pen)
        p.drawLine(0, horizon, w, horizon)

    def _draw_scene_elements(self, p, w, h, horizon):
        s = self.scene
        t = self.tick

        if s == "clear":
            self._draw_sun(p, w, horizon, t)
            self._draw_few_clouds(p, w, horizon, alpha=60)
            self._draw_trees(p, w, horizon)

        elif s == "cloudy":
            self._draw_sun(p, w, horizon, t, dim=True)
            self._draw_clouds(p, w, horizon, alpha=220)
            self._draw_trees(p, w, horizon)

        elif s in ("rain", "drizzle"):
            self._draw_clouds(p, w, horizon, alpha=230, dark=True)
            self._draw_rain(p, w, horizon,
                            intensity=0.6 if s == "drizzle" else 1.0)
            self._draw_trees(p, w, horizon, wet=True)

        elif s == "thunderstorm":
            self._draw_clouds(p, w, horizon, alpha=250, dark=True)
            self._draw_rain(p, w, horizon, intensity=1.0)
            if self.lightning:
                self._draw_lightning(p, w, horizon)
            self._draw_trees(p, w, horizon, wet=True)

        elif s == "snow":
            self._draw_sun(p, w, horizon, t, dim=True)
            self._draw_clouds(p, w, horizon, alpha=180)
            self._draw_snow(p, w, horizon)
            self._draw_snowy_trees(p, w, horizon)

        elif s == "fog":
            self._draw_fog(p, w, horizon)
            self._draw_trees(p, w, horizon)

        elif s == "haze":
            self._draw_sun(p, w, horizon, t, dim=True, haze=True)
            self._draw_trees(p, w, horizon)

    # ── ELEMENTOS ────────────────────────────
    def _draw_sun(self, p, w, horizon, t, dim=False, haze=False):
        cx = int(w * 0.78)
        cy = int(horizon * 0.28)
        r  = int(min(w, horizon) * 0.11)

        if haze:
            alpha = 160
            col   = QColor(255, 160, 60, alpha)
        elif dim:
            alpha = 200
            col   = QColor(255, 230, 80, alpha)
        else:
            alpha = 255
            col   = QColor(255, 215, 0, alpha)

        # Rayos
        if not haze:
            pen = QPen(QColor(255, 215, 0, 100 if dim else 160), 2)
            p.setPen(pen)
            for i in range(12):
                angle = math.radians(i * 30 + t * 0.3)
                r1, r2 = r + 6, r + 16 + (4 if not dim else 0)
                p.drawLine(
                    int(cx + r1 * math.cos(angle)), int(cy + r1 * math.sin(angle)),
                    int(cx + r2 * math.cos(angle)), int(cy + r2 * math.sin(angle))
                )

        grad = QRadialGradient(cx, cy, r)
        grad.setColorAt(0, col)
        grad.setColorAt(1, QColor(col.red(), col.green(), col.blue(), 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

    def _draw_clouds(self, p, w, horizon, alpha=200, dark=False):
        base = QColor(80, 80, 90, alpha) if dark else QColor(200, 200, 210, alpha)
        for (cx, cy, scale, _) in self.clouds:
            self._cloud_shape(p, int(cx * w), int(cy * horizon),
                               int(w * 0.12 * scale), base)

    def _draw_few_clouds(self, p, w, horizon, alpha=80):
        col = QColor(220, 230, 240, alpha)
        for i, (cx, cy, scale, _) in enumerate(self.clouds[:3]):
            self._cloud_shape(p, int(cx * w), int(cy * horizon),
                               int(w * 0.18 * scale), col)

    def _cloud_shape(self, p, cx, cy, size, color):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(color))
        for dx, dy, r in [
            (0, 0, 1.0), (-size//2, size//5, 0.7),
            (size//2, size//6, 0.75), (-size//4, -size//5, 0.8),
            (size//4, -size//4, 0.65),
        ]:
            rr = int(size * r)
            p.drawEllipse(cx + dx - rr, cy + dy - rr, rr * 2, rr * 2)

    def _draw_rain(self, p, w, horizon, intensity=1.0):
        count = int(len(self.drops) * intensity)
        pen = QPen(QColor(130, 170, 220, 160), 1)
        p.setPen(pen)
        for (rx, ry, _) in self.drops[:count]:
            x = int(rx * w)
            y = int(ry * horizon * 1.3)
            if y < horizon + 30:
                p.drawLine(x, y, x - 1, y + 10)

    def _draw_snow(self, p, w, horizon):
        p.setPen(Qt.PenStyle.NoPen)
        for (fx, fy, r, _) in self.flakes:
            x = int(fx * w)
            y = int(fy * (horizon + 30))
            if y < horizon + 10:
                p.setBrush(QBrush(QColor(255, 255, 255, 200)))
                p.drawEllipse(int(x - r/2), int(y - r/2), int(r), int(r))

    def _draw_fog(self, p, w, horizon):
        for i in range(5):
            y = int(horizon * (0.2 + i * 0.18))
            alpha = 60 + i * 15
            grad = QLinearGradient(0, y, w, y + 30)
            grad.setColorAt(0, QColor(200, 200, 200, 0))
            grad.setColorAt(0.3, QColor(200, 200, 200, alpha))
            grad.setColorAt(0.7, QColor(200, 200, 200, alpha))
            grad.setColorAt(1, QColor(200, 200, 200, 0))
            p.fillRect(0, y, w, 40, grad)

    def _draw_lightning(self, p, w, horizon):
        x = int(w * random.uniform(0.3, 0.7))
        pen = QPen(QColor(255, 255, 150, 220), 3)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(x, int(horizon * 0.3))
        path.lineTo(x - 12, int(horizon * 0.55))
        path.lineTo(x + 6,  int(horizon * 0.55))
        path.lineTo(x - 8,  int(horizon * 0.82))
        p.drawPath(path)

    def _draw_trees(self, p, w, horizon, wet=False):
        tree_col = QColor(34, 85, 34) if not wet else QColor(22, 66, 22)
        trunk_col = QColor(100, 70, 40)
        positions = [0.12, 0.22, 0.35, 0.62, 0.75, 0.88]
        for frac in positions:
            x = int(w * frac)
            h_tree = int((w * 0.07) * (0.8 + (frac * 3) % 0.4))
            trunk_w = max(4, h_tree // 8)
            # tronco
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(trunk_col))
            p.drawRect(x - trunk_w//2, horizon - h_tree//3, trunk_w, h_tree//3)
            # copa
            p.setBrush(QBrush(tree_col))
            for layer, (ly, lw) in enumerate([
                (h_tree, h_tree * 0.55),
                (h_tree * 0.65, h_tree * 0.7),
                (h_tree * 0.3, h_tree * 0.85),
            ]):
                top  = horizon - int(ly)
                half = int(lw / 2)
                path = QPainterPath()
                path.moveTo(x, top)
                path.lineTo(x + half, horizon - int(h_tree * 0.12 * layer))
                path.lineTo(x - half, horizon - int(h_tree * 0.12 * layer))
                path.closeSubpath()
                p.drawPath(path)

    def _draw_snowy_trees(self, p, w, horizon):
        self._draw_trees(p, w, horizon)
        # capa de nieve encima
        snow_col = QColor(230, 240, 255, 200)
        positions = [0.12, 0.22, 0.35, 0.62, 0.75, 0.88]
        for frac in positions:
            x = int(w * frac)
            h_tree = int((w * 0.07) * (0.8 + (frac * 3) % 0.4))
            top = horizon - h_tree
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(snow_col))
            path = QPainterPath()
            path.moveTo(x, top)
            path.lineTo(x + int(h_tree * 0.28), top + int(h_tree * 0.32))
            path.lineTo(x - int(h_tree * 0.28), top + int(h_tree * 0.32))
            path.closeSubpath()
            p.drawPath(path)


# ─────────────────────────────────────────────
#  VENTANA PRINCIPAL
# ─────────────────────────────────────────────
class ClimaEM(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clima EM")
        self.setMinimumSize(520, 660)
        self.resize(520, 720)
        self._apply_dark_theme()
        self._build_ui()

    # ── TEMA ─────────────────────────────────
    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget#root {
                background: #0f1923;
            }
            QLabel#title {
                color: #e2e8f0;
                font-size: 22px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QLabel#subtitle {
                color: #64748b;
                font-size: 11px;
                letter-spacing: 2px;
            }
            QLineEdit#search {
                background: #1e2a38;
                border: 1.5px solid #2d3d50;
                border-radius: 8px;
                color: #e2e8f0;
                font-size: 14px;
                padding: 10px 16px;
            }
            QLineEdit#search:focus {
                border-color: #3b82f6;
            }
            QPushButton#btn_search {
                background: #3b82f6;
                color: white;
                font-size: 13px;
                font-weight: 600;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton#btn_search:hover {
                background: #2563eb;
            }
            QPushButton#btn_search:pressed {
                background: #1d4ed8;
            }
            QPushButton#btn_search:disabled {
                background: #1e3a5f;
                color: #64748b;
            }
            QFrame#card {
                background: #162032;
                border: 1px solid #1e3a5f;
                border-radius: 16px;
            }
            QLabel#city_name {
                color: #e2e8f0;
                font-size: 20px;
                font-weight: 700;
            }
            QLabel#temp {
                color: #60a5fa;
                font-size: 42px;
                font-weight: 300;
            }
            QLabel#desc {
                color: #94a3b8;
                font-size: 13px;
                text-transform: capitalize;
            }
            QLabel#stat_label {
                color: #475569;
                font-size: 11px;
            }
            QLabel#stat_value {
                color: #cbd5e1;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#error_msg {
                color: #f87171;
                font-size: 12px;
            }
            QLabel#hint {
                color: #475569;
                font-size: 11px;
            }
        """)

    # ── UI ───────────────────────────────────
    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 28, 24, 24)
        layout.setSpacing(16)

        # Header
        title = QLabel("Clima EM")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sub = QLabel("WEATHER EXPLORER")
        sub.setObjectName("subtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        # Barra de búsqueda
        row = QHBoxLayout()
        row.setSpacing(8)
        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("Ingresa una ciudad... (ej: Tokyo, Ciudad de México)")
        self.search.returnPressed.connect(self._fetch)
        row.addWidget(self.search)

        self.btn = QPushButton("Escanear")
        self.btn.setObjectName("btn_search")
        self.btn.clicked.connect(self._fetch)
        self.btn.setFixedWidth(110)
        row.addWidget(self.btn)
        layout.addLayout(row)

        # Mensaje de error
        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("error_msg")
        self.error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_lbl.setVisible(False)
        layout.addWidget(self.error_lbl)

        # Tarjeta de datos
        self.card = QFrame()
        self.card.setObjectName("card")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(4)

        self.city_lbl = QLabel("—")
        self.city_lbl.setObjectName("city_name")
        self.city_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.city_lbl)

        self.temp_lbl = QLabel("—")
        self.temp_lbl.setObjectName("temp")
        self.temp_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.temp_lbl)

        self.desc_lbl = QLabel("—")
        self.desc_lbl.setObjectName("desc")
        self.desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.desc_lbl)

        # Stats grid
        stats_row = QHBoxLayout()
        stats_row.setSpacing(0)
        self._stat_widgets = {}
        for key, label in [("humidity","Humedad"), ("wind","Viento"), ("pressure","Presión"), ("feels","Se siente")]:
            col = QVBoxLayout()
            col.setSpacing(2)
            lbl = QLabel(label)
            lbl.setObjectName("stat_label")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val = QLabel("—")
            val.setObjectName("stat_value")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lbl)
            col.addWidget(val)
            stats_row.addLayout(col)
            self._stat_widgets[key] = val

        card_layout.addSpacing(8)
        card_layout.addLayout(stats_row)
        layout.addWidget(self.card)

        # Ilustración
        self.scene_widget = WeatherScene()
        self.scene_widget.setMinimumHeight(240)
        layout.addWidget(self.scene_widget)

        # Hint
        hint = QLabel("La ilustración cambia con el clima detectado")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

    # ── LÓGICA ───────────────────────────────
    def _fetch(self):
        city = self.search.text().strip()
        if not city:
            return
        self.btn.setEnabled(False)
        self.btn.setText("...")
        self.error_lbl.setVisible(False)

        self._worker = WeatherWorker(city)
        self._worker.result.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_result(self, data: dict):
        self.btn.setEnabled(True)
        self.btn.setText("Escanear")

        self.city_lbl.setText(f"{data['city']}, {data['country']}")
        self.temp_lbl.setText(f"{data['temp']:.1f}°C")
        self.desc_lbl.setText(data["description"].capitalize())
        self._stat_widgets["humidity"].setText(f"{data['humidity']}%")
        self._stat_widgets["wind"].setText(f"{data['wind']} m/s")
        self._stat_widgets["pressure"].setText(f"{data['pressure']} hPa")
        self._stat_widgets["feels"].setText(f"{data['feels_like']:.1f}°C")

        scene = condition_to_scene(data["condition"])
        self.scene_widget.set_scene(scene)

    def _on_error(self, msg: str):
        self.btn.setEnabled(True)
        self.btn.setText("Escanear")
        self.error_lbl.setText(f"⚠ {msg}")
        self.error_lbl.setVisible(True)


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Clima EM")
    window = ClimaEM()
    window.show()
    sys.exit(app.exec())
